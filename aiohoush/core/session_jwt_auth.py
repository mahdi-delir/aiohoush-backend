from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

from user.models import AuthSession

class SessionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        session_id = validated_token.get('sid')
        if not session_id:
            raise AuthenticationFailed(
                _("Token session is invalid.")
            )
        session_exists = AuthSession.objects.filter(
            pk=session_id,
            user=user,
            revoked_at__isnull=True,
        ).exists()
        if not session_exists:
            raise AuthenticationFailed(
                _("Token session has been revoked.")
            )
        return user

