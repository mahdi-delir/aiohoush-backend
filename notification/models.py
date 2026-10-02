from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# Create your models here.

class SMSServerResponse(models.Model):
    class SMSSTATUS(models.TextChoices):
        PENDING = "pending", _("در انتظار")
        SENT = "sent", _("ارسال شده")
        REJECTED = "rejected", _("عدم ارسال")
        FAILED = 'failed', _('خطا')
        TIMEOUT = 'timeout', _('تایم اوت')
        REQUESTED = 'requested', _('درخواست به سرویس دهنده')

    otp = models.ForeignKey(
        "notification.OTPSMSToken",
        on_delete=models.PROTECT,
        verbose_name=_("کد یکبار مصرف"),
        related_name="sms_attempts",
        blank=True,
        null=True
    )

    text = models.CharField(
        max_length=255,
        verbose_name=_("متن ارسالی"),
    )

    recipient = models.CharField(
        max_length=11,
        verbose_name=_("دریافت کننده"),
    )

    trace_id = models.BigAutoField(
        primary_key=True,
        verbose_name=_("کد پیگیری"),
    )

    status = models.CharField(
        max_length=10,
        verbose_name=_("وضعیت ارسال"),
        choices=SMSSTATUS.choices,
        default=SMSSTATUS.PENDING,
    )

    server_response = models.JSONField(
        verbose_name=_("پاسخ سرور اس ام اس"),
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("زمان ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("زمان آخرین تغییر"),
    )

    def __str__(self):
        return f"{self.text} -> {self.recipient} : {self.status}"

class OTPSMSToken(models.Model):
    class OTPREASON(models.TextChoices):
        LOGIN = "login", _("ورود")
        RESETPASSWORD = "reset_pass", _("بازنشانی گذرواژه")
        MOBILEVERIFY = "mobile_verify", _("تایید شماره موبایل")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("کاربر"),
        related_name="otps",
    )

    reason = models.CharField(
        max_length=20,
        verbose_name=_("دلیل درخواست کد"),
        choices=OTPREASON.choices,
    )

    code_hash = models.CharField(
        max_length=128,
        verbose_name=_("کد هش شده"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("زمان درخواست"),
    )

    expires_at = models.DateTimeField(
        verbose_name=_("تاریخ انقضاء کد"),
    )

    consumed_at = models.DateTimeField(
        verbose_name=_("زمان استفاده از کد"),
        blank=True,
        null=True,
    )
    revoked_at = models.DateTimeField(
        verbose_name=_("زمان ابطال"),
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user} -> {self.reason}"