from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models import Count, Q

from .models import Announcement, AnnouncementSettings, PushSubscription
from .services import announcements as service


class AnnouncementAdminForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = (
            "title", "body", "link", "audience",
            "groups", "users", "courses", "mentor", "send_sms",
        )

    request = None  # در get_form مقداردهی می‌شود

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        data = service.AnnouncementInput(
            title=cleaned.get("title") or "",
            body=cleaned.get("body") or "",
            audience=cleaned.get("audience") or "",
            link=cleaned.get("link") or "",
            group_ids=[group.pk for group in cleaned.get("groups") or []],
            user_ids=[user.pk for user in cleaned.get("users") or []],
            course_ids=[course.pk for course in cleaned.get("courses") or []],
            mentor_id=cleaned["mentor"].pk if cleaned.get("mentor") else None,
            send_sms=bool(cleaned.get("send_sms")),
        )
        try:
            valid = service.validate(self.request.user, data)
        except service.AnnouncementError as exc:
            raise ValidationError(str(exc))

        # فقط فیلدهای مربوط به مخاطب انتخاب‌شده ذخیره شوند.
        cleaned.update(
            title=valid["title"], body=valid["body"], link=valid["link"],
            groups=valid["groups"], users=valid["users"], courses=valid["courses"],
            mentor=valid["mentor"],
        )
        return cleaned


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ("title", "audience", "created_by", "recipient_count", "read_count", "send_sms", "created_at")
    list_filter = ("audience", "send_sms", "created_at")
    search_fields = ("title", "body", "created_by__mobile", "created_by__last_name")
    list_select_related = ("created_by",)
    raw_id_fields = ("users", "mentor")
    filter_horizontal = ("groups", "courses")

    fieldsets = (
        (None, {"fields": ("title", "body", "link")}),
        ("مخاطب", {
            "fields": ("audience", "groups", "users", "courses", "mentor"),
            "description": "بسته به «مخاطب» فقط یکی از گروه‌ها، افراد، دوره‌ها یا منتور لازم است.",
        }),
        ("ارسال", {"fields": ("send_sms",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _read_count=Count("recipients", filter=Q(recipients__read_at__isnull=False)),
        )

    @admin.display(description="خوانده‌شده", ordering="_read_count")
    def read_count(self, obj):
        return obj._read_count

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        # اعلان ارسال‌شده قابل ویرایش نیست.
        return (
            "title", "body", "link", "audience", "groups", "users", "courses",
            "mentor", "send_sms", "sender_label", "created_by", "recipient_count", "published_at", "created_at",
        )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.fieldsets
        return (
            (None, {"fields": ("title", "body", "link")}),
            ("مخاطب", {"fields": ("audience", "groups", "users", "courses", "mentor")}),
            ("وضعیت", {"fields": ("send_sms", "sender_label", "created_by", "recipient_count", "published_at", "created_at")}),
        )

    def has_change_permission(self, request, obj=None):
        # فقط مشاهده بعد از ارسال
        return obj is None and super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return bool(service.allowed_audiences(request.user))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        count = service.publish(form.instance)
        sms = " و پیامک در صف ارسال قرار گرفت" if form.instance.send_sms and count else ""
        self.message_user(request, f"اعلان برای {count:,} نفر ارسال شد{sms}.", level=messages.SUCCESS)


@admin.register(AnnouncementSettings)
class AnnouncementSettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ("sms_groups",)

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        # فقط یک ردیف تنظیمات وجود دارد؛ مستقیم صفحهٔ ویرایش همان باز شود.
        obj = AnnouncementSettings.load()
        return redirect(reverse("admin:announcement_announcementsettings_change", args=[obj.pk]))

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # فقط مدیر اصلی تعیین می‌کند چه گروهی پیامک بفرستد.
        return request.user.is_superuser


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """فقط مشاهده؛ دستگاه‌ها را خود کاربران فعال/غیرفعال می‌کنند."""

    list_display = ("user", "user_agent", "created_at", "last_success_at", "failure_count")
    search_fields = ("user__mobile", "user__last_name")
    list_select_related = ("user",)
    readonly_fields = ("user", "endpoint", "p256dh", "auth", "user_agent", "created_at", "last_success_at", "failure_count")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
