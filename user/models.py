from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
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
                                       verbose_name=_('تاریخ ایجاد؟'))

    date_updated = models.DateTimeField(auto_now=True,
                                        verbose_name=_('آخرین تغییر'))

    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('تاریخ تولد'))

    address = models.TextField(blank=True, null=True, verbose_name=_('آدرس پستی'))
    
    postal_code = models.CharField(max_length=10,
                                   blank=True,
                                   null=True,
                                   validators=[postal_code_validator],
                                   verbose_name='کد پستی')
    referral_code = models.ForeignKey(
        'user.ReferralCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='کد ورود هنگام ثبت نام',
        related_name = 'referred_users'
    )

    objects = UserManager()
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'mobile'
    EMAIL_FIELD = 'email'

    def active_groups_qs(self):
        return self.groups.filter(
            role__is_active=True,
            is_active=True
        ).distinct()

    def has_group(self, code: str) -> bool:
        return self.groups.filter(
            is_active=True,
            group__is_active=True,
            group__code=code,
        ).exists()

    def __str__(self):
        return f"${self.mobile} - ${self.first_name if self.first_name else None} ${self.last_name if self.last_name else None}"
