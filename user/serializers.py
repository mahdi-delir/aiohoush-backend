from uuid import UUID

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import Serializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed


from .models import User, AuthSession

mobile_model_field = User._meta.get_field("mobile")


class LoginOTPRequestSerializer(Serializer):
    mobile = serializers.CharField(
        max_length=mobile_model_field.max_length,
        validators=list(mobile_model_field.validators),
        trim_whitespace=False,
    )

class LoginOTPVerifySerializer(Serializer):
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
    def validate(self, attrs):
        refresh = self.token_class(
            attrs['refresh']
        )
        session_id = refresh.get('sid')
        user_id = refresh.get('user_id')
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

        AuthSession.objects.filter(
            pk=session.pk
        ).update(
            last_used_at=timezone.now()
        )

        return data