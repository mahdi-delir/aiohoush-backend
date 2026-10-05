import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from course.models import private_media_storage


def ticket_file_upload_to(instance, filename):
    # پسوند حفظ می‌شود؛ نام فایل تصادفی است.
    extension = Path(filename).suffix.lower()
    return (
        "tickets/"
        f"{instance.ticket_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )


class Ticket(models.Model):
    class DEPARTMENT(models.TextChoices):
        MENTOR = "mentor", "منتور"
        TEACHER = "teacher", "استاد"
        FINANCE = "finance", "واحد مالی"
        MANAGEMENT = "management", "مدیریت"

    class STATUS(models.TextChoices):
        WAITING = "waiting", "در انتظار پاسخ"
        ANSWERED = "answered", "پاسخ داده شده"
        CLOSED = "closed", "بسته شده"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="دانشجو",
    )

    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT.choices,
        verbose_name="بخش",
    )

    # منتور یا استاد مشخص؛ برای واحد مالی و مدیریت خالی (گروهی).
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tickets",
        blank=True,
        null=True,
        verbose_name="گیرنده",
    )

    course = models.ForeignKey(
        "course.Course",
        on_delete=models.PROTECT,
        related_name="tickets",
        blank=True,
        null=True,
        verbose_name="دوره (تیکت استاد)",
    )

    subject = models.CharField(
        max_length=150,
        verbose_name="موضوع",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS.choices,
        default=STATUS.WAITING,
        verbose_name="وضعیت",
    )

    last_message_at = models.DateTimeField(
        db_index=True,
        verbose_name="آخرین پیام",
    )

    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="زمان بسته شدن",
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="closed_tickets",
        blank=True,
        null=True,
        verbose_name="بسته شده توسط (خالی = خودکار)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت‌ها"
        ordering = ("-last_message_at",)
        indexes = [
            models.Index(fields=["student", "-last_message_at"], name="ticket_student_idx"),
            models.Index(fields=["department", "status"], name="ticket_department_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(department="teacher") | models.Q(course__isnull=False),
                name="teacher_ticket_has_course",
            ),
        ]

    def __str__(self):
        return f"#{self.pk} {self.subject}"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        "ticket.Ticket",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="تیکت",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_messages",
        verbose_name="نویسنده",
    )

    text = models.TextField(
        blank=True,
        verbose_name="متن",
    )

    # فایل‌ها در storage خصوصی؛ فقط از طریق endpoint دارای بررسی دسترسی.
    attachment = models.FileField(
        upload_to=ticket_file_upload_to,
        storage=private_media_storage,
        blank=True,
        null=True,
        verbose_name="پیوست",
    )

    attachment_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="نام اصلی پیوست",
    )

    voice = models.FileField(
        upload_to=ticket_file_upload_to,
        storage=private_media_storage,
        blank=True,
        null=True,
        verbose_name="پیام صوتی",
    )

    voice_duration_ms = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="مدت پیام صوتی (میلی‌ثانیه)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")

    class Meta:
        verbose_name = "پیام تیکت"
        verbose_name_plural = "پیام‌های تیکت"
        ordering = ("created_at", "id")

    @property
    def is_from_student(self) -> bool:
        return self.author_id == self.ticket.student_id

    def __str__(self):
        return f"#{self.ticket_id} - {self.author}"
