from uuid import UUID

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import (
    AuthenticationFailed,
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.settings import api_settings


from aiohoush.utilities.normalizers import normalize_mobile_to_09

from .models import User, AuthSession, UserProfilePicture

mobile_model_field = User._meta.get_field("mobile")


class MobileField(serializers.CharField):
    """شماره موبایل را به شکل استاندارد 09xxxxxxxxx تبدیل می‌کند.

    9121234567، 09121234567، 989121234567، +989121234567 و شکل فارسی
    ارقام همه یک کاربر حساب می‌شوند.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("validators", list(mobile_model_field.validators))
        kwargs.setdefault("trim_whitespace", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)

        try:
            return normalize_mobile_to_09(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class LoginOTPRequestSerializer(serializers.Serializer):
    mobile = MobileField()

class LoginOTPVerifySerializer(serializers.Serializer):
    mobile = MobileField()

    code = serializers.RegexField(
        regex=rf"^\d{{{settings.OTP_LENGTH}}}$",
        min_length=settings.OTP_LENGTH,
        max_length=settings.OTP_LENGTH,
        trim_whitespace=False,
    )

class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    default_error_messages = {
        **TokenRefreshSerializer.default_error_messages,
        "invalid_session": _("نشست کاربر معتبر نیست."),
    }
    @transaction.atomic
    def validate(self, attrs):
        # توکن منقضی، دستکاری‌شده یا blacklist‌شده باید 401 بدهد، نه 500.
        # BFF با پاسخ 4xx نشست را پاک و کاربر را به ورود هدایت می‌کند.
        try:
            return self._validate(attrs)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

    def _validate(self, attrs):
        refresh = self.token_class(
            attrs['refresh']
        )
        session_id = refresh.get('sid')
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        if not session_id or not user_id:
            raise AuthenticationFailed(
                self.error_messages["invalid_session"],
                code="invalid_session",
            )

        try:
            session_uuid = UUID(str(session_id))
        except (ValueError, TypeError, AttributeError):
            raise AuthenticationFailed(
                self.error_messages["invalid_session"],
                code="invalid_session",
            )
        session = (
            AuthSession.objects
            .select_for_update()
            .filter(
                id=session_uuid,
                user_id=user_id,
                revoked_at__isnull=True,
            )
            .first()
        )
        if session is None:
            raise AuthenticationFailed(
                self.error_messages["invalid_session"],
                code="invalid_session",
            )
        data = super().validate(attrs)
        if "refresh" in data:
            new_refresh = self.token_class(
                data["refresh"]
            )

            session.refresh_jti = new_refresh[
                api_settings.JTI_CLAIM
            ]

        session.last_used_at = timezone.now()

        session.save(
            update_fields=[
                "refresh_jti",
                "last_used_at",
            ]
        )
        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

class AuthSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = (
            "id",
            "ip_address",
            "browser_name",
            "browser_version",
            "os_name",
            "os_version",
            "device_type",
            "device_brand",
            "device_model",
            "created_at",
            "last_used_at",
            "is_current",
        )

    def get_is_current(self, obj):
        current_sid = self.context.get(
            "current_sid"
        )

        return str(obj.id) == str(current_sid)

class CurrentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    mobile = serializers.CharField()

class ActiveCourseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    all_sessions = serializers.IntegerField()
    current_session = serializers.IntegerField()
    completed_percent = serializers.FloatField()

class UserDataSerializer(serializers.Serializer):
    watched_gift = serializers.BooleanField(
        required=False,
    )
    has_course = serializers.BooleanField(
        required=False,
    )
    active_courses = ActiveCourseSerializer(
        many=True,
        required=False,
    )

class MeResponseSerializer(serializers.Serializer):
    user = CurrentUserSerializer()
    groups = serializers.ListField(
        child=serializers.CharField(),
    )
    permissions = serializers.ListField(
        child=serializers.CharField(),
    )
    user_data = UserDataSerializer()
class ProfileSerializer(serializers.ModelSerializer):
    # validator مدل بعد از نرمال‌سازی (حذف @ و لینک t.me) اجرا می‌شود.
    telegram_id = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = (
            "id", "first_name", "last_name", "mobile", "email",
            "national_id", "telegram_id", "address", "bio", "is_profile_completed",
        )
        read_only_fields = ("id", "mobile", "is_profile_completed")

    def validate_telegram_id(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from aiohoush.utilities.validators import (
            normalize_telegram_id,
            telegram_id_validator,
        )

        value = normalize_telegram_id(value)
        if not value:
            return None
        try:
            telegram_id_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate_email(self, value):
        return value or None

    def validate_national_id(self, value):
        from aiohoush.utilities.digits import normalize_number_to_en
        value = normalize_number_to_en(value or "")
        if value:
            User._meta.get_field("national_id").run_validators(value)
        return value or None

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.is_profile_completed = bool(
            (instance.first_name or "").strip()
            and (instance.last_name or "").strip()
        )
        instance.save()
        return instance


class ProfilePictureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfilePicture
        fields = ("id", "url", "created_at")
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.picture.url) if request else obj.picture.url
