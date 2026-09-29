from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from aiohoush.utilities.normalizers import normalize_mobile_to_09
from aiohoush.utilities.validators import mobile_validator, national_id_validator, postal_code_validator
# Create your models here.

class Group(models.Model):
    """
    Group model
    Fields:
    code, title, is_active, created_at
    نقش های سراسری مثل مدیرعامل شریک کارمند استاد دانشجو و ...
    """
    code = models.SlugField(unique=True, max_length=50)
    title = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"
    
class UserManager(BaseUserManager):
    def creat_user(self, mobile, password = None, **kwargs):
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
        return self.creat_user(mobile, password, **kwargs)

class User(AbstractBaseUser, PermissionsMixin):
    mobile=models.CharField(max_length=11,
                            unique=True,
                            verbose_name=_('شماره موبایل'),
                            validators=[mobile_validator])
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
    
    date_joined = models.DateTimeField(auto_now_add=True,
                                       verbose_name=_('زمان ایجاد؟'))

    date_updated = models.DateTimeField(auto_now=True,
                                        verbose_name=_('زمان آخرین تغییر'))

    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('تاریخ تولد'))

    address = models.TextField(blank=True, null=True, verbose_name=_('آدرس پستی'))
    
    postal_code = models.CharField(max_length=10,
                                   blank=True,
                                   null=True,
                                   validators=[postal_code_validator],
                                   verbose_name=_('کد پستی'))
    referral_code = models.ForeignKey(
        'user.ReferralCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('کد معرف هنگام ثبت نام'),
        related_name = 'referred_users'
    )

    groups = models.ManyToManyField('user.Group', verbose_name='گروه ها', related_name='users')

    objects = UserManager()
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'mobile'
    EMAIL_FIELD = 'email'

    def user_pictures_qs(self):
        return self.profile_pictures.filter(is_deleted = False).distinct()

    def __str__(self):
        return f"${self.mobile} - ${self.first_name if self.first_name else None} ${self.last_name if self.last_name else None}"

class UserProfilePicture(models.Model):
    user = models.ForeignKey('settings.AUTH_USER_MODEL', on_delete=models.CASCADE, verbose_name=_('کاربر'), related_name='profile_pictures')
    picture = models.ImageField(upload_to='profilepictures/', verbose_name=_('عکس پروفایل'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ بارگزاری'))
    is_deleted = models.BooleanField(default=False, verbose_name=_('حذف شده'))

    def get_user_pictures(self, user):
        return self
    def __str__(self):
        return f"${self.user.mobile} - ${self.first_name if self.first_name else None} ${self.last_name if self.last_name else None}"

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
    student = models.ForeignKey('settings.AUTH_USER_MODEL', on_delete=models.CASCADE, related_name='mentor_assignments', verbose_name=_('دانش آموز'))
    mentor = models.ForeignKey('settings.AUTH_USER_MODEL', on_delete=models.PROTECT, related_name='mentored_students_history', verbose_name=_('منتور'))
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
            ]

    def __str__(self):
        return f"{self.student.mobile} - {self.student.first_name if self.student.first_name else None} {self.student.last_name if self.student.last_name else None} -> {self.mentor.mobile} - {self.mentor.first_name if self.mentor.first_name else None}"

