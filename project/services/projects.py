"""پروژه‌های آیوهوش و دانشجویان.

- پروژهٔ آیوهوش فقط از پنل ادمین ساخته می‌شود و فایل قابل دانلود ندارد.
- پروژهٔ دانشجو از پنل ثبت می‌شود و بعد از تأیید نمایش داده می‌شود.
  هر تغییری (متن، عکس، فایل) آن را دوباره «در انتظار تأیید» می‌کند و
  تا تأیید دوباره در گالری نیست.
- رد شدن با دلیل است و دانشجو پیامک می‌گیرد.
- zip پروژه را فقط صاحب پروژه، مدرس دورهٔ پروژه و کسی که مجوز
  view_project_files دارد (مدیر اصلی) دانلود می‌کند.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from aiohoush.utilities.uploads import validate_project_file, validate_project_image
from course.models import Course
from project.models import Project, ProjectFile, ProjectImage, Technology


MAX_TITLE_LENGTH = 150
MAX_DESCRIPTION_LENGTH = 5000
MAX_REASON_LENGTH = 1000


class ProjectError(Exception):
    """خطای قابل‌نمایش به کاربر."""


# --- دسترسی ----------------------------------------------------------------

def visible_projects():
    """پروژه‌هایی که در گالری دیده می‌شوند."""
    return Project.objects.filter(is_deleted=False, status=Project.STATUS.APPROVED)


def can_view(user, project: Project) -> bool:
    if project.is_deleted:
        return False
    if project.status == Project.STATUS.APPROVED:
        return True
    return project.owner_id == user.pk or user.has_perm("project.review_project")


def can_download_files(user, project: Project) -> bool:
    if project.is_deleted:
        return False
    if project.owner_id is not None and project.owner_id == user.pk:
        return True
    if project.course_id is not None and project.course.teacher_id == user.pk:
        return True
    return user.has_perm("project.view_project_files")


# --- گزینه‌های فرم -----------------------------------------------------------

def purchased_courses(student):
    from order.models import Order

    return list(
        Course.objects
        .filter(
            requested_products__order__student=student,
            requested_products__order__status=Order.STATUS.APPROVED,
            requested_products__order__is_deleted=False,
        )
        .distinct()
        .order_by("order", "id")
    )


def active_technologies():
    return list(Technology.objects.filter(is_active=True))


# --- اعتبارسنجی ----------------------------------------------------------------

_https_url = URLValidator(schemes=["https"])


def _clean_url(value, *, github: bool) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    try:
        _https_url(value)
    except DjangoValidationError:
        raise ProjectError("لینک باید یک آدرس https معتبر باشد.")

    if github:
        host = value.split("/")[2].lower()
        if host not in {"github.com", "www.github.com"}:
            raise ProjectError("لینک GitHub باید از github.com باشد.")

    return value


def _clean_fields(*, student, data: dict) -> dict:
    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()

    if not title:
        raise ProjectError("عنوان پروژه را وارد کنید.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ProjectError(f"عنوان پروژه حداکثر {MAX_TITLE_LENGTH} کاراکتر است.")
    if not description:
        raise ProjectError("توضیحات پروژه را وارد کنید.")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ProjectError(f"توضیحات پروژه حداکثر {MAX_DESCRIPTION_LENGTH} کاراکتر است.")

    # دوره اختیاری است و فقط از دوره‌های خریداری‌شدهٔ خود دانشجو.
    course = None
    course_id = data.get("course")
    if course_id not in (None, "", "null"):
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            raise ProjectError("دوره معتبر نیست.")
        course = next(
            (item for item in purchased_courses(student) if item.pk == course_id),
            None,
        )
        if course is None:
            raise ProjectError("فقط دوره‌هایی که خریده‌اید قابل انتخاب است.")

    raw_technologies = data.get("technologies") or []
    try:
        technology_ids = {int(item) for item in raw_technologies}
    except (TypeError, ValueError):
        raise ProjectError("فناوری‌ها معتبر نیستند.")

    technologies = list(Technology.objects.filter(pk__in=technology_ids, is_active=True))
    if len(technologies) != len(technology_ids):
        raise ProjectError("فناوری انتخاب‌شده معتبر نیست.")

    return {
        "title": title,
        "description": description,
        "course": course,
        "technologies": technologies,
        "github_url": _clean_url(data.get("github_url"), github=True),
        "demo_url": _clean_url(data.get("demo_url"), github=False),
    }


def _validated_image(file):
    try:
        extension = validate_project_image(file)
    except DjangoValidationError as exc:
        raise ProjectError(exc.messages[0])
    file.name = f"image{extension}"
    return file


def _validated_zip(file):
    try:
        validate_project_file(file)
    except DjangoValidationError as exc:
        raise ProjectError(exc.messages[0])
    return file


# --- عملیات دانشجو -------------------------------------------------------------

def _resubmit(project: Project) -> None:
    project.status = Project.STATUS.PENDING
    project.submitted_at = timezone.now()
    project.rejection_reason = ""
    project.reviewed_by = None
    project.reviewed_at = None


def _own_project_for_update(*, student, project_id: int) -> Project:
    project = (
        Project.objects
        .select_for_update()
        .filter(pk=project_id, owner=student, kind=Project.KIND.STUDENT, is_deleted=False)
        .first()
    )
    if project is None:
        raise ProjectError("پروژه پیدا نشد.")
    return project


def _save_resubmitted(project: Project, *extra_fields: str) -> None:
    _resubmit(project)
    project.save(update_fields=[
        "status", "submitted_at", "rejection_reason", "reviewed_by",
        "reviewed_at", "updated_at", *extra_fields,
    ])


@transaction.atomic
def create_student_project(*, student, data: dict, images: list, files: list) -> Project:
    fields = _clean_fields(student=student, data=data)

    if not images:
        raise ProjectError("حداقل یک عکس از پروژه لازم است.")

    images = [_validated_image(image) for image in images]
    files = [_validated_zip(file) for file in files]

    technologies = fields.pop("technologies")
    project = Project.objects.create(
        kind=Project.KIND.STUDENT,
        owner=student,
        status=Project.STATUS.PENDING,
        submitted_at=timezone.now(),
        **fields,
    )
    project.technologies.set(technologies)

    for image in images:
        ProjectImage.objects.create(project=project, image=image)

    for file in files:
        _create_file(project, file)

    return project


@transaction.atomic
def update_student_project(*, student, project_id: int, data: dict) -> Project:
    project = _own_project_for_update(student=student, project_id=project_id)
    fields = _clean_fields(student=student, data=data)
    technologies = fields.pop("technologies")

    for name, value in fields.items():
        setattr(project, name, value)

    _save_resubmitted(project, *fields.keys())
    project.technologies.set(technologies)

    return project


@transaction.atomic
def add_image(*, student, project_id: int, image) -> ProjectImage:
    project = _own_project_for_update(student=student, project_id=project_id)
    created = ProjectImage.objects.create(project=project, image=_validated_image(image))
    _save_resubmitted(project)
    return created


@transaction.atomic
def remove_image(*, student, project_id: int, image_id: int) -> None:
    project = _own_project_for_update(student=student, project_id=project_id)
    image = project.images.filter(pk=image_id).first()

    if image is None:
        raise ProjectError("عکس پیدا نشد.")
    if project.images.count() <= 1:
        raise ProjectError("پروژه باید حداقل یک عکس داشته باشد.")

    stored = image.image
    image.delete()
    _save_resubmitted(project)
    transaction.on_commit(lambda: stored.delete(save=False))


def _create_file(project: Project, file) -> ProjectFile:
    return ProjectFile.objects.create(
        project=project,
        file=file,
        original_name=file.name[:255],
        size=file.size,
    )


@transaction.atomic
def add_file(*, student, project_id: int, file) -> ProjectFile:
    project = _own_project_for_update(student=student, project_id=project_id)
    created = _create_file(project, _validated_zip(file))
    _save_resubmitted(project)
    return created


@transaction.atomic
def remove_file(*, student, project_id: int, file_id: int) -> None:
    project = _own_project_for_update(student=student, project_id=project_id)
    item = project.files.filter(pk=file_id).first()

    if item is None:
        raise ProjectError("فایل پیدا نشد.")

    stored = item.file
    item.delete()
    _save_resubmitted(project)
    transaction.on_commit(lambda: stored.delete(save=False))


@transaction.atomic
def delete_student_project(*, student, project_id: int) -> None:
    # حذف نرم: سابقه می‌ماند ولی هیچ‌جا نمایش داده نمی‌شود.
    project = _own_project_for_update(student=student, project_id=project_id)
    project.is_deleted = True
    project.deleted_at = timezone.now()
    project.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


# --- بررسی (فعلاً از پنل ادمین) ---------------------------------------------------

@transaction.atomic
def review_project(*, project_id: int, by, approve: bool, reason: str = "") -> Project:
    project = (
        Project.objects
        .select_for_update()
        .filter(pk=project_id, kind=Project.KIND.STUDENT, is_deleted=False)
        .first()
    )
    if project is None:
        raise ProjectError("پروژه پیدا نشد.")

    reason = (reason or "").strip()

    if approve:
        if project.status == Project.STATUS.APPROVED:
            return project
        project.status = Project.STATUS.APPROVED
        project.rejection_reason = ""
    else:
        if not reason:
            raise ProjectError("برای رد پروژه، دلیل را بنویسید.")
        if len(reason) > MAX_REASON_LENGTH:
            raise ProjectError(f"دلیل رد حداکثر {MAX_REASON_LENGTH} کاراکتر است.")
        project.status = Project.STATUS.REJECTED
        project.rejection_reason = reason

    project.reviewed_by = by
    project.reviewed_at = timezone.now()
    project.save(update_fields=[
        "status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at",
    ])

    if not approve:
        from notification.tasks import send_project_sms

        send_project_sms.delay_on_commit(project_id=project.pk, event="rejected")

    return project


# --- جست‌وجوی گالری -------------------------------------------------------------

def search_gallery(*, kind: str, query: str, technology_id: int | None):
    projects = visible_projects().filter(kind=kind)

    if technology_id:
        projects = projects.filter(technologies__pk=technology_id)

    for term in query.split():
        projects = projects.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(technologies__title__icontains=term)
            | Q(owner__first_name__icontains=term)
            | Q(owner__last_name__icontains=term)
            | Q(course__title__icontains=term)
        )

    return projects.distinct()
