from uuid import UUID

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings


from .models import User, AuthSession

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
        session.last_used_at = timezone.now()
        session.save(
            update_fields=["last_used_at"]
        )

        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )