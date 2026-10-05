"""تیکت دانشجو به منتور، استاد، واحد مالی و مدیریت.

- پیام دانشجو → وضعیت «در انتظار پاسخ»
- پیام پاسخ‌دهنده → وضعیت «پاسخ داده شده» + پیامک به دانشجو
- فقط دانشجو تیکت را می‌بندد؛ یک هفته بعد از آخرین پیام خودکار بسته می‌شود.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from aiohoush.utilities.uploads import (
    validate_ticket_attachment,
    validate_voice_message,
)
from course.access import has_purchased_course
from course.models import Course
from ticket.models import Ticket, TicketMessage
from user.services.mentor import full_name, get_active_mentor


AUTO_CLOSE_AFTER = timedelta(days=7)

MAX_TEXT_LENGTH = 5000


class TicketError(Exception):
    """خطای قابل‌نمایش به کاربر."""


# --- بسته شدن خودکار ---------------------------------------------------------

def close_stale_tickets(queryset=None) -> int:
    """تیکت‌هایی که یک هفته از آخرین پیامشان گذشته بسته می‌شوند."""
    queryset = queryset if queryset is not None else Ticket.objects.all()
    now = timezone.now()

    return (
        queryset
        .exclude(status=Ticket.STATUS.CLOSED)
        .filter(last_message_at__lt=now - AUTO_CLOSE_AFTER)
        .update(status=Ticket.STATUS.CLOSED, closed_at=now, closed_by=None)
    )


# --- گزینه‌های ایجاد تیکت ----------------------------------------------------

def purchased_courses(student):
    from order.models import Order

    return list(
        Course.objects
        .filter(
            requested_products__order__student=student,
            requested_products__order__status=Order.STATUS.APPROVED,
            requested_products__order__is_deleted=False,
        )
        .select_related("teacher")
        .distinct()
        .order_by("order", "id")
    )


def department_options(student) -> dict:
    mentor = get_active_mentor(student)

    return {
        "mentor": (
            {"id": mentor.pk, "name": full_name(mentor)}
            if mentor
            else None
        ),
        "courses": [
            {
                "id": course.pk,
                "title": course.title,
                "teacherName": full_name(course.teacher),
            }
            for course in purchased_courses(student)
        ],
    }


# --- پیام‌ها -----------------------------------------------------------------

def _validate_content(*, text: str, attachment, voice, voice_duration_ms):
    text = (text or "").strip()

    if not text and not attachment and not voice:
        raise TicketError("متن پیام، فایل یا پیام صوتی را وارد کنید.")

    if len(text) > MAX_TEXT_LENGTH:
        raise TicketError(f"متن پیام نباید بیشتر از {MAX_TEXT_LENGTH} حرف باشد.")

    try:
        if attachment:
            validate_ticket_attachment(attachment)
        if voice:
            validate_voice_message(voice)
    except DjangoValidationError as exc:
        raise TicketError(exc.messages[0])

    if voice_duration_ms is not None and not 0 <= voice_duration_ms <= 60 * 60 * 1000:
        voice_duration_ms = None

    return text, voice_duration_ms


def _create_message(*, ticket, author, text, attachment, voice, voice_duration_ms):
    return TicketMessage.objects.create(
        ticket=ticket,
        author=author,
        text=text,
        attachment=attachment or None,
        attachment_name=(attachment.name[:255] if attachment else ""),
        voice=voice or None,
        voice_duration_ms=voice_duration_ms if voice else None,
    )


@transaction.atomic
def create_ticket(
    *,
    student,
    department: str,
    course_id,
    subject: str,
    text: str,
    attachment=None,
    voice=None,
    voice_duration_ms=None,
) -> Ticket:
    from notification.tasks import send_ticket_sms

    subject = (subject or "").strip()
    if not subject:
        raise TicketError("موضوع تیکت را وارد کنید.")
    if len(subject) > 150:
        raise TicketError("موضوع تیکت نباید بیشتر از ۱۵۰ حرف باشد.")

    if department not in Ticket.DEPARTMENT.values:
        raise TicketError("بخش انتخاب‌شده معتبر نیست.")

    text, voice_duration_ms = _validate_content(
        text=text,
        attachment=attachment,
        voice=voice,
        voice_duration_ms=voice_duration_ms,
    )

    assigned_to = None
    course = None

    if department == Ticket.DEPARTMENT.MENTOR:
        assigned_to = get_active_mentor(student)
        if assigned_to is None:
            raise TicketError("هنوز منتوری برای شما تعیین نشده است.")

    elif department == Ticket.DEPARTMENT.TEACHER:
        course = (
            Course.objects.select_related("teacher").filter(pk=course_id).first()
            if str(course_id or "").isdigit()
            else None
        )
        if course is None or not has_purchased_course(student, course):
            raise TicketError("دورهٔ انتخاب‌شده معتبر نیست.")
        assigned_to = course.teacher

    ticket = Ticket.objects.create(
        student=student,
        department=department,
        assigned_to=assigned_to,
        course=course,
        subject=subject,
        status=Ticket.STATUS.WAITING,
        last_message_at=timezone.now(),
    )

    _create_message(
        ticket=ticket,
        author=student,
        text=text,
        attachment=attachment,
        voice=voice,
        voice_duration_ms=voice_duration_ms,
    )

    send_ticket_sms.delay_on_commit(ticket_id=ticket.pk, event="created")

    return ticket


@transaction.atomic
def add_message(
    *,
    ticket_id: int,
    author,
    text: str,
    attachment=None,
    voice=None,
    voice_duration_ms=None,
) -> TicketMessage:
    from notification.tasks import send_ticket_sms

    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)

    # اگر یک هفته گذشته، قبل از پیام جدید بسته می‌شود.
    close_stale_tickets(Ticket.objects.filter(pk=ticket.pk))
    ticket.refresh_from_db()

    if ticket.status == Ticket.STATUS.CLOSED:
        raise TicketError("این تیکت بسته شده است؛ برای ادامه تیکت جدید ثبت کنید.")

    text, voice_duration_ms = _validate_content(
        text=text,
        attachment=attachment,
        voice=voice,
        voice_duration_ms=voice_duration_ms,
    )

    message = _create_message(
        ticket=ticket,
        author=author,
        text=text,
        attachment=attachment,
        voice=voice,
        voice_duration_ms=voice_duration_ms,
    )

    is_student = author.pk == ticket.student_id

    ticket.status = (
        Ticket.STATUS.WAITING if is_student else Ticket.STATUS.ANSWERED
    )
    ticket.last_message_at = message.created_at
    ticket.save(update_fields=["status", "last_message_at", "updated_at"])

    if not is_student:
        send_ticket_sms.delay_on_commit(ticket_id=ticket.pk, event="answered")

    return message


@transaction.atomic
def close_ticket(*, ticket_id: int, by) -> Ticket:
    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)

    # فقط خود دانشجو می‌تواند تیکت را ببندد.
    if ticket.student_id != by.pk:
        raise TicketError("فقط ایجادکنندهٔ تیکت می‌تواند آن را ببندد.")

    if ticket.status != Ticket.STATUS.CLOSED:
        ticket.status = Ticket.STATUS.CLOSED
        ticket.closed_at = timezone.now()
        ticket.closed_by = by
        ticket.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])

    return ticket


def recipient_label(ticket: Ticket) -> str:
    if ticket.assigned_to_id:
        return full_name(ticket.assigned_to)
    return ticket.get_department_display()
