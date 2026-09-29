from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class SuperuserAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_superuser:
            raise ValidationError(
                _("اجازهٔ ورود به این پنل را ندارید."),
                code="admin_access_denied",
            )


class AiohoushAdminSite(AdminSite):
    site_header = _("مدیریت آیوهوش")
    site_title = _("آیوهوش")
    index_title = _("پنل مدیریت")

    login_form = SuperuserAdminAuthenticationForm

    def has_permission(self, request):
        return (
            super().has_permission(request)
            and request.user.is_superuser
        )