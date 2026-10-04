from uuid import UUID

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings


from .models import User, AuthSession, UserProfilePicture

mobile_model_field = User._meta.get_field("mobile")


class LoginOTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=mobile_model_field.max_length,
        validators=list(mobile_model_field.validators),
        trim_whitespace=False,
    )

class LoginOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=mobile_model_field.max_length,
        validators=list(mobile_model_field.validators),
        trim_whitespace=False,
    )

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
        refresh = self.token_class(
            attrs['refresh']
        )
        session_id = refresh.get('sid')
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        if not session_id or not user_id:
            raise AuthenticationFailed(
                self.error_messages[_("invalid_session")],
                code="invalid_session",
            )

        try:
            session_uuid = UUID(str(session_id))
        except (ValueError, TypeError, AttributeError):
            raise AuthenticationFailed(
                self.error_messages[_("invalid_session")],
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
                self.error_messages[_("invalid_session")],
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
    class Meta:
        model = User
        fields = (
            "id", "first_name", "last_name", "mobile", "email",
            "national_id", "address", "bio", "is_profile_completed",
        )
        read_only_fields = ("id", "mobile", "is_profile_completed")

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
