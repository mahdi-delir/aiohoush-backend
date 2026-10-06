"""اعلان‌ها (زنگولهٔ اپ) و پیامک اختیاری.

مخاطب‌ها:
- همهٔ کاربران                        ← مجوز send_announcement_all
- یک یا چند گروه (هر گروه موجود)       ← مجوز send_announcement_groups
- افراد مشخص                          ← مجوز send_announcement_users
- خریداران دوره‌ها                     ← send_announcement_course_students
  (فقط دوره‌های خود استاد؛ با send_announcement_any_course هر دوره‌ای)
- دانشجوهایی که منتورشان است           ← send_announcement_mentees
  (فقط دانشجوهای خود فرستنده؛ با send_announcement_any_mentor هر منتوری)

گیرندگان همان لحظهٔ ارسال ثبت می‌شوند؛ کسی که بعداً عضو گروه شود اعلان
قبلی را نمی‌بیند. پیامک فقط برای superuser و اعضای گروه‌هایی که در
«تنظیمات اعلان‌ها» انتخاب شده‌اند.
"""

from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from announcement.models import Announcement, AnnouncementRecipient, AnnouncementSettings
from course.models import Course
from user.models import StudentMentorAssignment, User


MAX_TITLE_LENGTH = 150
MAX_BODY_LENGTH = 2000
MAX_LINK_LENGTH = 300
RECIPIENT_BATCH_SIZE = 1000

AUDIENCE = Announcement.AUDIENCE


class AnnouncementError(Exception):
    """خطای قابل‌نمایش به کاربر."""


@dataclass
class AnnouncementInput:
    title: str
    body: str
    audience: str
    link: str = ""
    group_ids: list[int] = field(default_factory=list)
    user_ids: list[int] = field(default_factory=list)
    course_ids: list[int] = field(default_factory=list)
    mentor_id: int | None = None
    send_sms: bool = False


# --- مجوزها -------------------------------------------------------------------

def _perm(user, codename: str) -> bool:
    return user.has_perm(f"announcement.{codename}")


def allowed_audiences(user) -> list[str]:
    allowed = []
    if _perm(user, "send_announcement_all"):
        allowed.append(AUDIENCE.ALL)
    if _perm(user, "send_announcement_groups"):
        allowed.append(AUDIENCE.GROUPS)
    if _perm(user, "send_announcement_users"):
        allowed.append(AUDIENCE.USERS)
    if _perm(user, "send_announcement_course_students") or _perm(user, "send_announcement_any_course"):
        allowed.append(AUDIENCE.COURSE_STUDENTS)
    if _perm(user, "send_announcement_mentees") or _perm(user, "send_announcement_any_mentor"):
        allowed.append(AUDIENCE.MENTEES)
    return allowed


def can_send_sms(user) -> bool:
    if user.is_superuser:
        return True
    sms_group_ids = set(AnnouncementSettings.load().sms_groups.values_list("pk", flat=True))
    return bool(sms_group_ids) and user.groups.filter(pk__in=sms_group_ids).exists()


def sendable_courses(user):
    courses = Course.objects.order_by("order", "id")
    if _perm(user, "send_announcement_any_course"):
        return courses
    return courses.filter(teacher=user)


def compose_options(user) -> dict:
    audiences = allowed_audiences(user)
    return {
        "audiences": [
            {"value": value, "label": AUDIENCE(value).label}
            for value in audiences
        ],
        "groups": (
            [{"id": group.pk, "name": group.name} for group in Group.objects.order_by("name")]
            if AUDIENCE.GROUPS in audiences
            else []
        ),
        "courses": (
            [{"id": course.pk, "title": course.title} for course in sendable_courses(user)]
            if AUDIENCE.COURSE_STUDENTS in audiences
            else []
        ),
        "canChooseMentor": _perm(user, "send_announcement_any_mentor"),
        "canSendSms": can_send_sms(user),
    }


# --- اعتبارسنجی ----------------------------------------------------------------

def _clean_link(link: str) -> str:
    link = (link or "").strip()
    if not link:
        return ""
    if len(link) > MAX_LINK_LENGTH:
        raise AnnouncementError("لینک بیش از حد طولانی است.")
    if link.startswith("/") and not link.startswith("//"):
        return link
    if link.startswith("https://") and " " not in link:
        return link
    raise AnnouncementError("لینک باید یک مسیر داخلی اپ (مثل /dashboard/courses) یا آدرس https باشد.")


def validate(sender, data: AnnouncementInput) -> dict:
    """ورودی را بر اساس مجوزهای فرستنده بررسی می‌کند و مقادیر تمیز را برمی‌گرداند."""
    title = (data.title or "").strip()
    body = (data.body or "").strip()

    if not title:
        raise AnnouncementError("عنوان اعلان را وارد کنید.")
    if len(title) > MAX_TITLE_LENGTH:
        raise AnnouncementError(f"عنوان حداکثر {MAX_TITLE_LENGTH} کاراکتر است.")
    if not body:
        raise AnnouncementError("متن اعلان را وارد کنید.")
    if len(body) > MAX_BODY_LENGTH:
        raise AnnouncementError(f"متن حداکثر {MAX_BODY_LENGTH} کاراکتر است.")

    audience = data.audience
    if audience not in allowed_audiences(sender):
        raise AnnouncementError("اجازهٔ ارسال اعلان به این مخاطب را ندارید.")

    cleaned = {
        "title": title,
        "body": body,
        "link": _clean_link(data.link),
        "audience": audience,
        "groups": [],
        "users": [],
        "courses": [],
        "mentor": None,
        "send_sms": bool(data.send_sms),
    }

    if audience == AUDIENCE.GROUPS:
        ids = set(data.group_ids)
        groups = list(Group.objects.filter(pk__in=ids))
        if not ids or len(groups) != len(ids):
            raise AnnouncementError("حداقل یک گروه معتبر انتخاب کنید.")
        cleaned["groups"] = groups

    elif audience == AUDIENCE.USERS:
        ids = set(data.user_ids)
        users = list(User.objects.filter(pk__in=ids, is_active=True))
        if not ids or len(users) != len(ids):
            raise AnnouncementError("حداقل یک کاربر معتبر انتخاب کنید.")
        cleaned["users"] = users

    elif audience == AUDIENCE.COURSE_STUDENTS:
        ids = set(data.course_ids)
        courses = list(sendable_courses(sender).filter(pk__in=ids))
        if not ids or len(courses) != len(ids):
            raise AnnouncementError("فقط دوره‌های خودتان قابل انتخاب است.")
        cleaned["courses"] = courses

    elif audience == AUDIENCE.MENTEES:
        mentor = sender
        if data.mentor_id and data.mentor_id != sender.pk:
            if not _perm(sender, "send_announcement_any_mentor"):
                raise AnnouncementError("فقط به دانشجوهای خودتان می‌توانید اعلان بدهید.")
            mentor = User.objects.filter(pk=data.mentor_id).first()
            if mentor is None:
                raise AnnouncementError("منتور پیدا نشد.")
        cleaned["mentor"] = mentor

    if cleaned["send_sms"] and not can_send_sms(sender):
        raise AnnouncementError("اجازهٔ ارسال پیامک برای اعلان را ندارید.")

    return cleaned


# --- گیرندگان -------------------------------------------------------------------

def recipient_ids(announcement: Announcement) -> list[int]:
    from order.models import Order

    active = User.objects.filter(is_active=True)
    audience = announcement.audience

    if audience == AUDIENCE.ALL:
        users = active
    elif audience == AUDIENCE.GROUPS:
        users = active.filter(groups__in=announcement.groups.all())
    elif audience == AUDIENCE.USERS:
        users = active.filter(pk__in=announcement.users.values("pk"))
    elif audience == AUDIENCE.COURSE_STUDENTS:
        users = active.filter(
            orders__status=Order.STATUS.APPROVED,
            orders__is_deleted=False,
            orders__requested_products__course__in=announcement.courses.all(),
        )
    elif audience == AUDIENCE.MENTEES:
        users = active.filter(
            pk__in=StudentMentorAssignment.objects.filter(
                mentor=announcement.mentor, is_active=True,
            ).values("student_id")
        )
    else:
        raise AnnouncementError("مخاطب نامعتبر است.")

    return list(users.values_list("pk", flat=True).distinct())


# --- انتشار ---------------------------------------------------------------------

@transaction.atomic
def publish(announcement: Announcement) -> int:
    """گیرندگان را ثبت می‌کند (فقط یک بار) و در صورت نیاز پیامک را صف می‌کند."""
    announcement = Announcement.objects.select_for_update().get(pk=announcement.pk)
    if announcement.published_at is not None:
        return announcement.recipient_count

    ids = recipient_ids(announcement)

    for start in range(0, len(ids), RECIPIENT_BATCH_SIZE):
        AnnouncementRecipient.objects.bulk_create(
            [
                AnnouncementRecipient(announcement=announcement, user_id=user_id)
                for user_id in ids[start:start + RECIPIENT_BATCH_SIZE]
            ],
            ignore_conflicts=True,
        )

    announcement.recipient_count = len(ids)
    announcement.published_at = timezone.now()
    announcement.sender_label = compute_sender_label(announcement)
    announcement.save(update_fields=["recipient_count", "published_at", "sender_label"])

    if announcement.send_sms and ids:
        from announcement.tasks import send_announcement_sms

        send_announcement_sms.delay_on_commit(announcement_id=announcement.pk)

    return len(ids)


@transaction.atomic
def create_and_publish(*, sender, data: AnnouncementInput) -> Announcement:
    cleaned = validate(sender, data)
    groups = cleaned.pop("groups")
    users = cleaned.pop("users")
    courses = cleaned.pop("courses")

    announcement = Announcement.objects.create(created_by=sender, **cleaned)
    announcement.groups.set(groups)
    announcement.users.set(users)
    announcement.courses.set(courses)

    publish(announcement)
    announcement.refresh_from_db()
    return announcement


# --- صندوق کاربر ------------------------------------------------------------------

def inbox(user):
    return (
        AnnouncementRecipient.objects
        .filter(user=user)
        .select_related("announcement")
        .order_by("-created_at", "-id")
    )


def unread_count(user) -> int:
    return AnnouncementRecipient.objects.filter(user=user, read_at__isnull=True).count()


def mark_read(*, user, announcement_id: int) -> bool:
    updated = (
        AnnouncementRecipient.objects
        .filter(user=user, announcement_id=announcement_id, read_at__isnull=True)
        .update(read_at=timezone.now())
    )
    exists = updated or AnnouncementRecipient.objects.filter(
        user=user, announcement_id=announcement_id,
    ).exists()
    return bool(exists)


def mark_all_read(user) -> int:
    return (
        AnnouncementRecipient.objects
        .filter(user=user, read_at__isnull=True)
        .update(read_at=timezone.now())
    )


def compute_sender_label(announcement: Announcement) -> str:
    """نام شخص فقط وقتی که خودش استاد همان دوره‌ها یا منتور همان دانشجوها است."""
    from user.services.mentor import full_name

    sender = announcement.created_by

    if announcement.audience == AUDIENCE.COURSE_STUDENTS:
        teacher_ids = set(announcement.courses.values_list("teacher_id", flat=True))
        if teacher_ids == {sender.pk}:
            return f"استاد {full_name(sender)}"

    if announcement.audience == AUDIENCE.MENTEES and announcement.mentor_id == sender.pk:
        return f"منتور {full_name(sender)}"

    return "آیوهوش"


def sender_label(announcement: Announcement) -> str:
    return announcement.sender_label or "آیوهوش"


def sms_text(announcement: Announcement) -> str:
    link = f"{settings.APP_ORIGIN.rstrip('/')}/dashboard/notifications"
    return f"{announcement.title}\n{link}"
