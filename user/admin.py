from django.contrib import admin
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .models import MentorRequest, MentorReview, StudentMentorAssignment, User


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
        (_('اطلاعات تماس و معرفی'), {'fields': ('telegram_id', 'address', 'postal_code', 'referral_code')}),
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


@admin.register(StudentMentorAssignment)
class StudentMentorAssignmentAdmin(admin.ModelAdmin):
    """اتصال دانشجو به منتور.

    با ثبت اتصال فعال جدید، اتصال فعال قبلی همان دانشجو خودکار پایان
    می‌یابد (هر دانشجو فقط یک منتور فعال دارد).
    """

    list_display = ('id', 'student', 'mentor', 'is_active', 'started_at', 'ended_at', 'assigned_by')
    list_filter = ('is_active', 'started_at')
    search_fields = ('student__mobile', 'student__last_name', 'mentor__mobile', 'mentor__last_name')
    list_select_related = ('student', 'mentor', 'assigned_by')
    raw_id_fields = ('student', 'mentor')
    readonly_fields = ('started_at', 'ended_at', 'assigned_by', 'is_active')
    fields = ('student', 'mentor', 'reason', 'is_active', 'started_at', 'ended_at', 'assigned_by')
    actions = ('end_selected',)

    def has_change_permission(self, request, obj=None):
        # تاریخچه تغییر نمی‌کند؛ برای عوض کردن منتور، اتصال جدید ثبت کنید.
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not change:
            StudentMentorAssignment.objects.select_for_update().filter(
                student=obj.student,
                is_active=True,
            ).update(
                is_active=False,
                ended_at=timezone.now(),
            )
            obj.assigned_by = request.user
            obj.is_active = True

            # درخواست منتور باز این دانشجو رسیدگی‌شده حساب می‌شود.
            MentorRequest.objects.filter(
                student=obj.student,
                status=MentorRequest.STATUS.OPEN,
            ).update(
                status=MentorRequest.STATUS.DONE,
                handled_by=request.user,
                handled_at=timezone.now(),
            )
        super().save_model(request, obj, form, change)

    @admin.action(description=_('پایان اتصال‌های انتخاب‌شده'))
    def end_selected(self, request, queryset):
        count = queryset.filter(is_active=True).update(
            is_active=False,
            ended_at=timezone.now(),
        )
        self.message_user(request, _('%(count)d اتصال پایان یافت.') % {'count': count})


@admin.register(MentorReview)
class MentorReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentor', 'student', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating', 'created_at')
    search_fields = ('mentor__mobile', 'mentor__last_name', 'student__mobile', 'text')
    list_select_related = ('mentor', 'student')
    list_editable = ('is_published',)
    readonly_fields = ('mentor', 'student', 'rating', 'text', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False


@admin.register(MentorRequest)
class MentorRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'status', 'created_at', 'handled_by', 'handled_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__mobile', 'student__last_name')
    list_select_related = ('student', 'handled_by')
    readonly_fields = ('student', 'status', 'created_at', 'handled_by', 'handled_at')
    actions = ('mark_done',)

    def has_add_permission(self, request):
        return False

    @admin.action(description=_('علامت‌گذاری به‌عنوان رسیدگی‌شده'))
    def mark_done(self, request, queryset):
        count = queryset.filter(status=MentorRequest.STATUS.OPEN).update(
            status=MentorRequest.STATUS.DONE,
            handled_by=request.user,
            handled_at=timezone.now(),
        )
        self.message_user(request, _('%(count)d درخواست رسیدگی شد.') % {'count': count})
