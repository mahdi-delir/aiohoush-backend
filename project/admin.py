from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import path, reverse
from django.utils.html import format_html

from aiohoush.utilities.uploads import validate_project_image

from .models import Project, ProjectFile, ProjectImage, Technology
from .services import projects as project_service
from .views import file_response


CONTENT_FIELDS = (
    "title", "description", "course", "technologies", "github_url", "demo_url",
)


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("title",)


def _is_student(obj) -> bool:
    return obj is not None and obj.kind == Project.KIND.STUDENT


class ProjectImageForm(forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ("image",)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # فقط فایل تازه آپلودشده بررسی می‌شود، نه عکس قبلی.
        if image and hasattr(image, "content_type"):
            extension = validate_project_image(image)
            image.name = f"image{extension}"
        return image


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    form = ProjectImageForm
    extra = 0
    min_num = 1
    validate_min = True
    fields = ("preview", "image")
    readonly_fields = ("preview",)

    def get_formset(self, request, obj=None, **kwargs):
        # ادمین جنگو validate_min را خودش به formset نمی‌دهد؛ بدون آن
        # پروژهٔ بدون عکس هم ذخیره می‌شد.
        kwargs["validate_min"] = True
        return super().get_formset(request, obj, **kwargs)

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return "-"
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener"><img src="{0}" style="max-height:90px;border-radius:6px"></a>',
            obj.image.url,
        )

    # عکس‌های پروژهٔ دانشجو را فقط خود دانشجو تغییر می‌دهد.
    def has_add_permission(self, request, obj=None):
        return not _is_student(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not _is_student(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not _is_student(obj) and super().has_delete_permission(request, obj)


class ProjectFileInline(admin.TabularInline):
    model = ProjectFile
    extra = 0
    fields = ("original_name", "size_text", "created_at", "download")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="حجم")
    def size_text(self, obj):
        return f"{obj.size / (1024 * 1024):.1f} مگابایت"

    @admin.display(description="دانلود")
    def download(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:project_projectfile_download", args=[obj.pk])
        return format_html('<a href="{}">دانلود</a>', url)


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status", getattr(self.instance, "status", None))
        reason = (cleaned.get("rejection_reason") or "").strip()

        if _is_student(self.instance) and status == Project.STATUS.REJECTED and not reason:
            raise ValidationError({"rejection_reason": "برای رد پروژه، دلیل را بنویسید."})

        return cleaned


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ("title", "kind", "owner", "course", "status", "created_at")
    list_filter = ("kind", "status", "is_deleted")
    search_fields = ("title", "owner__mobile", "owner__last_name", "course__title")
    list_select_related = ("owner", "course")
    filter_horizontal = ("technologies",)
    inlines = (ProjectImageInline, ProjectFileInline)
    actions = ("approve_selected",)

    fields = (
        "kind", "owner", "status", "rejection_reason",
        *CONTENT_FIELDS,
        "submitted_at", "reviewed_by", "reviewed_at",
        "is_deleted", "deleted_at", "created_at", "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner", "course")

    def get_readonly_fields(self, request, obj=None):
        readonly = [
            "kind", "owner", "submitted_at", "reviewed_by", "reviewed_at",
            "is_deleted", "deleted_at", "created_at", "updated_at",
        ]
        if _is_student(obj):
            readonly += CONTENT_FIELDS
            if not request.user.has_perm("project.review_project"):
                readonly += ["status", "rejection_reason"]
        return readonly

    def get_changeform_initial_data(self, request):
        # پروژهٔ آیوهوش از ادمین مستقیم منتشر می‌شود.
        return {"status": Project.STATUS.APPROVED}

    def has_delete_permission(self, request, obj=None):
        # پروژهٔ دانشجو را فقط خودش حذف می‌کند (حذف نرم).
        return not _is_student(obj) and super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not _is_student(obj):
            obj.kind = Project.KIND.AIOHOUSH
            obj.owner = None
            return super().save_model(request, obj, form, change)

        # پروژهٔ دانشجو: فقط تأیید/رد، از طریق سرویس (ثبت بررسی‌کننده + پیامک).
        if not {"status", "rejection_reason"} & set(form.changed_data):
            return

        if obj.status == Project.STATUS.PENDING:
            self.message_user(
                request,
                "وضعیت «در انتظار تأیید» را فقط ویرایش دانشجو تنظیم می‌کند.",
                level=messages.WARNING,
            )
            return

        try:
            project_service.review_project(
                project_id=obj.pk,
                by=request.user,
                approve=obj.status == Project.STATUS.APPROVED,
                reason=obj.rejection_reason,
            )
        except project_service.ProjectError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)

    @admin.action(description="تأیید پروژه‌های دانشجویی انتخاب‌شده", permissions=["review"])
    def approve_selected(self, request, queryset):
        approved = 0
        for project in queryset.filter(kind=Project.KIND.STUDENT, is_deleted=False):
            project_service.review_project(project_id=project.pk, by=request.user, approve=True)
            approved += 1
        self.message_user(request, f"{approved} پروژه تأیید شد.")

    def has_review_permission(self, request):
        return request.user.has_perm("project.review_project")

    # --- دانلود zip از ادمین ------------------------------------------------

    def get_urls(self):
        return [
            path(
                "files/<int:file_id>/download/",
                self.admin_site.admin_view(self.download_file),
                name="project_projectfile_download",
            ),
            *super().get_urls(),
        ]

    def download_file(self, request, file_id):
        item = (
            ProjectFile.objects
            .select_related("project__course")
            .filter(pk=file_id)
            .first()
        )
        if item is None or not project_service.can_download_files(request.user, item.project):
            raise PermissionDenied
        return file_response(item)
