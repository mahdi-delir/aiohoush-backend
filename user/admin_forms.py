from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from aiohoush.utilities.normalizers import normalize_mobile_to_09
from .models import User


_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


class MobileField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        return normalize_mobile_to_09(value) if value else value


class DigitsField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        return value.translate(_DIGITS) if value else None


class UserAdminFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('user_permissions', 'denied_permissions'):
            if name in self.fields:
                self.fields[name].queryset = self.fields[name].queryset.select_related('content_type')

    def clean_email(self):
        return self.cleaned_data.get('email') or None


class UserAdminCreationForm(UserAdminFormMixin, AdminUserCreationForm):
    mobile = MobileField(label=_('شماره موبایل'), max_length=11)

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ('mobile',)
        field_classes = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usable_password'].initial = 'false'


class UserAdminChangeForm(UserAdminFormMixin, UserChangeForm):
    mobile = MobileField(label=_('شماره موبایل'), max_length=11)
    national_id = DigitsField(label=_('کد ملی'), max_length=10, required=False)
    postal_code = DigitsField(label=_('کد پستی'), max_length=10, required=False)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
        field_classes = {}
