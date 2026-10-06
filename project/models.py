import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from course.models import private_media_storage


def _project_folder(project) -> str:
    owner = project.owner.mobile if project.owner_id else "aiohoush"
    return f"projects/{owner}/{project.pk}"


def project_image_upload_to(instance, filename):
    # پسوند از قبل با validate_project_image از روی محتوا تعیین شده است.
    extension = Path(filename).suffix.lower()
    return f"{_project_folder(instance.project)}/{uuid.uuid4().hex}{extension}"


def project_file_upload_to(instance, filename):
    return f"{_project_folder(instance.project)}/{uuid.uuid4().hex}.zip"


class Technology(models.Model):
    """فناوری‌هایی که برای پروژه انتخاب می‌شوند؛ لیست از ادمین مدیریت می‌شود."""

    title = models.CharField(max_length=50, unique=True, verbose_name="عنوان")
    order = models.PositiveIntegerField(default=1, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "فناوری"
        verbose_name_plural = "فناوری‌ها"
        ordering = ("order", "title")

    def __str__(self):
        return self.title


class Project(models.Model):
    class KIND(models.TextChoices):
        AIOHOUSH = "aiohoush", "پروژهٔ آیوهوش"
        STUDENT = "student", "پروژهٔ دانشجو"

    class STATUS(models.TextChoices):
        PENDING = "pending", "در انتظار تأیید"
        APPROVED = "approved", "تأیید شده"
        REJECTED = "rejected", "رد شده"

    kind = models.CharField(
        max_length=10,
        choices=KIND.choices,
        default=KIND.AIOHOUSH,
        verbose_name="نوع",
    )

    # برای پروژهٔ آیوهوش خالی است.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name="دانشجو",
    )

    # استاد پروژه = مدرس این دوره
    course = models.ForeignKey(
        "course.Course",
        on_delete=models.SET_NULL,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name="دوره",
    )

    title = models.CharField(max_length=150, verbose_name="عنوان")
    description = models.TextField(verbose_name="توضیحات")

    technologies = models.ManyToManyField(
        "project.Technology",
        related_name="projects",
        blank=True,
        verbose_name="فناوری‌ها",
    )

    github_url = models.URLField(blank=True, verbose_name="لینک GitHub")
    demo_url = models.URLField(blank=True, verbose_name="لینک دمو")

    status = models.CharField(
        max_length=10,
        choices=STATUS.choices,
        default=STATUS.PENDING,
        db_index=True,
        verbose_name="وضعیت",
    )

    rejection_reason = models.TextField(blank=True, verbose_name="دلیل رد")

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_projects",
        blank=True,
        null=True,
        verbose_name="بررسی‌کننده",
    )

    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان بررسی")

    # آخرین باری که دانشجو پروژه را برای بررسی فرستاد (ثبت یا ویرایش)
    submitted_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال برای بررسی")

    is_deleted = models.BooleanField(default=False, verbose_name="حذف شده")
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان حذف")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ("-created_at",)
        permissions = [
            ("review_project", "Can approve or reject student projects"),
            ("view_project_files", "Can download files of any project"),
        ]
        indexes = [
            models.Index(fields=["kind", "status", "-created_at"], name="project_gallery_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(kind="student") | models.Q(owner__isnull=False),
                name="student_project_has_owner",
            ),
        ]

    def __str__(self):
        return self.title


class ProjectImage(models.Model):
    project = models.ForeignKey(
        "project.Project",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="پروژه",
    )

    image = models.ImageField(upload_to=project_image_upload_to, verbose_name="تصویر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")

    class Meta:
        verbose_name = "تصویر پروژه"
        verbose_name_plural = "تصاویر پروژه"
        ordering = ("id",)

    def __str__(self):
        return f"{self.project} - {self.pk}"


class ProjectFile(models.Model):
    project = models.ForeignKey(
        "project.Project",
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="پروژه",
    )

    # storage خصوصی؛ دانلود فقط برای صاحب پروژه، استاد دوره و مدیر.
    file = models.FileField(
        upload_to=project_file_upload_to,
        storage=private_media_storage,
        verbose_name="فایل",
    )

    original_name = models.CharField(max_length=255, verbose_name="نام اصلی فایل")
    size = models.PositiveBigIntegerField(verbose_name="حجم (بایت)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")

    class Meta:
        verbose_name = "فایل پروژه"
        verbose_name_plural = "فایل‌های پروژه"
        ordering = ("id",)

    def __str__(self):
        return self.original_name
