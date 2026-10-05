"""صفحهٔ «منتور من» دانشجو: منتور فعلی، نظرها و درخواست منتور."""

from django.db import IntegrityError, transaction

from user.models import (
    MentorRequest,
    MentorReview,
    StudentMentorAssignment,
    User,
)


class MentorActionError(Exception):
    """خطای قابل‌نمایش به کاربر."""


def get_active_mentor(student: User) -> User | None:
    assignment = (
        StudentMentorAssignment.objects
        .filter(student=student, is_active=True)
        .select_related("mentor")
        .first()
    )
    return assignment.mentor if assignment else None


def full_name(user: User) -> str:
    name = " ".join(
        part.strip()
        for part in (user.first_name, user.last_name)
        if part and part.strip()
    )
    return name or "کاربر آیوهوش"


def avatar_url(user: User, request) -> str | None:
    picture = user.user_pictures_qs().first()
    if picture is None:
        return None
    return request.build_absolute_uri(picture.picture.url)


def submit_review(*, student: User, rating: int, text: str) -> MentorReview:
    mentor = get_active_mentor(student)

    if mentor is None:
        raise MentorActionError("هنوز منتوری برای شما تعیین نشده است.")

    if MentorReview.objects.filter(mentor=mentor, student=student).exists():
        raise MentorActionError("شما قبلاً برای این منتور نظر ثبت کرده‌اید.")

    try:
        with transaction.atomic():
            return MentorReview.objects.create(
                mentor=mentor,
                student=student,
                rating=rating,
                text=text.strip(),
            )
    except IntegrityError:
        # دو درخواست همزمان
        raise MentorActionError("شما قبلاً برای این منتور نظر ثبت کرده‌اید.")


def request_mentor(*, student: User) -> MentorRequest:
    if get_active_mentor(student) is not None:
        raise MentorActionError("شما در حال حاضر منتور دارید.")

    existing = MentorRequest.objects.filter(
        student=student,
        status=MentorRequest.STATUS.OPEN,
    ).first()

    if existing:
        return existing

    try:
        with transaction.atomic():
            return MentorRequest.objects.create(student=student)
    except IntegrityError:
        return MentorRequest.objects.get(
            student=student,
            status=MentorRequest.STATUS.OPEN,
        )
