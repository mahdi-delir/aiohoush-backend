from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models


class AnnouncementSettings(models.Model):
    """تنظیمات اعلان‌ها (یک ردیف). sync_role به این دست نمی‌زند."""

    sms_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="+",
        verbose_name="گروه‌هایی که اجازهٔ ارسال پیامک دارند",
        help_text="اعضای این گروه‌ها هنگام ارسال اعلان می‌توانند «ارسال پیامک» را هم انتخاب کنند. مدیر اصلی (superuser) همیشه اجازه دارد.",
    )

    class Meta:
        verbose_name = "تنظیمات اعلان‌ها"
        verbose_name_plural = "تنظیمات اعلان‌ها"

    def __str__(self):
        return "تنظیمات اعلان‌ها"

    @classmethod
    def load(cls) -> "AnnouncementSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Announcement(models.Model):
    class AUDIENCE(models.TextChoices):
        ALL = "all", "همهٔ کاربران"
        GROUPS = "groups", "گروه‌های انتخاب‌شده"
        USERS = "users", "افراد مشخص"
        COURSE_STUDENTS = "course_students", "خریداران دوره‌های انتخاب‌شده"
        MENTEES = "mentees", "دانشجوهای یک منتور"

    title = models.CharField(max_length=150, verbose_name="عنوان")
    body = models.TextField(verbose_name="متن")

    # مسیر داخلی اپ (مثلاً /dashboard/courses) یا آدرس https
    link = models.CharField(max_length=300, blank=True, verbose_name="لینک (اختیاری)")

    audience = models.CharField(max_length=20, choices=AUDIENCE.choices, verbose_name="مخاطب")

    groups = models.ManyToManyField(
        Group, blank=True, related_name="announcements", verbose_name="گروه‌ها",
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="+", verbose_name="افراد",
    )
    courses = models.ManyToManyField(
        "course.Course", blank=True, related_name="announcements", verbose_name="دوره‌ها",
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
        verbose_name="منتور (برای «دانشجوهای یک منتور»)",
    )

    send_sms = models.BooleanField(default=False, verbose_name="ارسال پیامک")

    # نام فرستنده‌ای که گیرنده می‌بیند؛ هنگام انتشار ثبت می‌شود.
    sender_label = models.CharField(max_length=150, blank=True, verbose_name="نام فرستنده برای گیرنده")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_announcements",
        verbose_name="فرستنده",
    )
    recipient_count = models.PositiveIntegerField(default=0, verbose_name="تعداد گیرندگان")
    published_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان انتشار")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ("-created_at",)
        permissions = [
            ("send_announcement_all", "Can send announcement to all users"),
            ("send_announcement_groups", "Can send announcement to any groups"),
            ("send_announcement_users", "Can send announcement to specific users"),
            ("send_announcement_course_students", "Can send announcement to own course students"),
            ("send_announcement_any_course", "Can send announcement to students of any course"),
            ("send_announcement_mentees", "Can send announcement to own mentees"),
            ("send_announcement_any_mentor", "Can send announcement to mentees of any mentor"),
        ]

    def __str__(self):
        return self.title


class AnnouncementRecipient(models.Model):
    """گیرندگان همان لحظهٔ ارسال (اعضای بعدی گروه اعلان قبلی را نمی‌بینند)."""

    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="recipients", verbose_name="اعلان",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcement_inbox",
        verbose_name="گیرنده",
    )
    read_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان خواندن")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان دریافت")

    class Meta:
        verbose_name = "گیرندهٔ اعلان"
        verbose_name_plural = "گیرندگان اعلان"
        constraints = [
            models.UniqueConstraint(fields=["announcement", "user"], name="unique_announcement_recipient"),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="announcement_inbox_idx"),
            models.Index(fields=["user", "read_at"], name="announcement_unread_idx"),
        ]

    def __str__(self):
        return f"{self.announcement} → {self.user}"
