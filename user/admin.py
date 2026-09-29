from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    list_display = ('pk','mobile', 'first_name', 'last_name', 'is_active', 'is_mobile_verified')
    list_filter = ('is_active', 'is_mobile_verified', 'is_superuser', 'is_staff', 'groups')
    search_fields = ('mobile', 'first_name', 'last_name', 'email', 'national_id')
    ordering = ('-pk',)
    readonly_fields = ('last_login', 'date_joined', 'date_updated')
    filter_horizontal = ('groups', 'user_permissions', 'denied_permissions')
    raw_id_fields = ('referral_code',)
    list_per_page = 50
    fieldsets = (
        (None, {'fields': ('mobile', 'password')}),
        (_('اطلاعات شخصی'), {'fields': ('first_name', 'last_name', 'email', 'national_id', 'date_of_birth')}),
        (_('اطلاعات تماس و معرفی'), {'fields': ('address', 'postal_code', 'referral_code')}),
        (_('وضعیت حساب'), {'fields': ('is_active', 'is_mobile_verified')}),
        (_('دسترسی‌ها'), {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions', 'denied_permissions'),
            'description': _('مجوزهای مستقیم به مجوزهای گروه‌ها اضافه می‌شوند؛ مجوزهای ممنوع‌شده با بک‌اند سفارشی از دسترسی کاربر عادی کم می‌شوند. سوپریوزر از این ممنوعیت‌ها مستثناست.'),
        }),
        (_('تاریخ‌ها'), {'fields': ('last_login', 'date_joined', 'date_updated')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile', 'usable_password', 'password1', 'password2'),
            'description': _('ابتدا حساب را بسازید؛ سپس اطلاعات شخصی، گروه‌ها و مجوزها را در صفحهٔ ویرایش تعیین کنید. غیرفعال بودن ورود با رمز ثابت به‌تنهایی ورود پیامکی را پیاده‌سازی نمی‌کند.'),
        }),
    )
