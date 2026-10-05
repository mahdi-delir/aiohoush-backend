import uuid

from pathlib import Path

from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from aiohoush.utilities.normalizers import normalize_mobile_to_09
from aiohoush.utilities.validators import mobile_validator, national_id_validator, postal_code_validator
# Create your models here.

def user_avatar_upload_to(
    instance,
    filename,
):
    # نام اصلی فایل کنار گذاشته می‌شود؛ پسوند از قبل توسط
    # validate_profile_picture از روی محتوای تصویر تعیین شده است.
    extension = Path(filename).suffix.lower()

    return (
        "avatars/"
        f"{instance.user.mobile}/"
        f"{uuid.uuid4().hex}{extension}"
    )

class UserManager(BaseUserManager):
    def create_user(self, mobile, password = None, **kwargs):
        if not mobile:
            raise ValueError(_('شماره موبایل برای ساخت کاربر الزامی است.'))
        mobile = normalize_mobile_to_09(mobile)
        user = self.model(mobile = mobile, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)
        kwargs.setdefault('is_active', True)
        kwargs.setdefault('is_mobile_verified', True)

        if kwargs.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if kwargs.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(mobile, password, **kwargs)

class User(AbstractBaseUser, PermissionsMixin):
    denied_permissions = models.ManyToManyField(
            "auth.Permission",
            blank=True,
            related_name="users_denied_permission",
            verbose_name=_("مجوزهای ممنوع‌شده"),
            help_text=_(
                "این مجوزها حتی در صورت دریافت از گروه یا مجوز مستقیم "
                "ممنوع هستند. روی superuser فعال اثری ندارند."
            ),
        )
    mobile=models.CharField(
        max_length=11,
        unique=True,
        verbose_name=_('شماره موبایل'),
        validators=[mobile_validator]
        )
    first_name = models.CharField(max_length=50,
                                  blank=True,
                                  null=True,
                                  verbose_name=_('نام'))
    last_name = models.CharField(max_length=70,
                                 blank=True,
                                 null=True,
                                 verbose_name=_('نام خانوادگی'))
    email = models.EmailField(max_length=254,
                             unique=True,
                             verbose_name=_('ایمیل'),
                             null=True,
                             blank=True)
    national_id=models.CharField(max_length=10,
                                 unique=True,
                                 verbose_name=_('کد ملی'),
                                 null=True,
                                 blank=True,
                                 validators=[national_id_validator])
    is_staff = models.BooleanField(default=False, verbose_name=_('دسترسی ادمین پنل؟'))

    is_active = models.BooleanField(default=True,
                                    verbose_name=_('فعال؟'))
    
    is_mobile_verified = models.BooleanField(default=False,
                                      verbose_name=_('موبایل تایید شده است؟'))

    is_profile_completed = models.BooleanField(
        default=False,
        verbose_name=_('پروفایل تکمیل شده است؟')
    )
    
    date_joined = models.DateTimeField(auto_now_add=True,
                                       verbose_name=_('زمان ایجاد؟'))

    date_updated = models.DateTimeField(auto_now=True,
                                        verbose_name=_('زمان آخرین تغییر'))

    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('تاریخ تولد'))

    address = models.TextField(blank=True, null=True, verbose_name=_('آدرس پستی'))

    bio = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('بیوگرافی')
    )

    postal_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[postal_code_validator],
        verbose_name=_('کد پستی')
    )

    referral_code = models.ForeignKey(
        'user.ReferralCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('کد معرف هنگام ثبت نام'),
        related_name = 'referred_users'
    )

    objects = UserManager()
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'mobile'
    EMAIL_FIELD = 'email'

    def user_pictures_qs(self):
        return self.profile_pictures.filter(is_deleted = False).order_by('-id')

    def __str__(self):
        full_name = " ".join(
            part for part in (self.first_name, self.last_name) if part
        )
        return f"{self.mobile} - {full_name}" if full_name else self.mobile

class UserProfilePicture(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='profile_pictures'
    )

    picture = models.ImageField(
        upload_to=user_avatar_upload_to,
        verbose_name=_('عکس پروفایل')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاریخ بارگزاری')
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('حذف شده')
    )

    def __str__(self):
        return f"عکس پروفایل {self.user}"

class ReferralCode(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name="owned_referral_codes",
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('کد معرف')
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("عنوان کد")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاریخ ایجاد کد')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('فعال بودن کد')
    )

class StudentMentorAssignment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_assignments', verbose_name=_('دانش آموز'))
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mentored_students_history', verbose_name=_('منتور'))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ شروع'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاریخ پایان'))
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_mentor_assignments_created",
        verbose_name=_('کاربر متصل کننده')
    )
    reason = models.TextField(blank=True, null=True, verbose_name=_('علت'))
    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(student=models.F("mentor")),
                name="student_mentor_must_differ",
            ),
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(is_active=True),
                name="unique_active_mentor_per_student",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_active=True, ended_at__isnull=True)
                    | models.Q(is_active=False, ended_at__isnull=False)
                ),
                name="mentor_assignment_status_matches_end",
                violation_error_message=_(
                    "تخصیص فعال نباید تاریخ پایان داشته باشد؛ "
                    "تخصیص پایان‌یافته باید تاریخ پایان داشته باشد."
                ),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(ended_at__isnull=True)
                    | models.Q(ended_at__gte=models.F("started_at"))
                ),
                name="mentor_assignment_end_after_start",
                violation_error_message=_(
                    "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.student} → {self.mentor}"

class AuthSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auth_sessions',
        verbose_name=_('کاربر')
    )
    refresh_jti = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("شناسه Refresh Token فعلی"),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("آدرس IP"),
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
    )

    browser_name = models.CharField(
            max_length=100,
            blank=True,
            verbose_name=_('نام مرورگر')
        )
    
    browser_version = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("نسخه مرورگر"),
    )

    os_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("سیستم عامل"),
    )

    os_version = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("نسخه سیستم عامل"),
    )

    device_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('نوع دستگاه')
    )

    device_brand = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('برند دستگاه')
    )

    device_model = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('مدل دستگاه')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('زمان ایجاد')
    )
    
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('زمان آخرین استفاده')
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('زمان ابطال')
    )
    def __str__(self):
        return f"{self.user} - {self.id}"

