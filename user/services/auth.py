from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from notification.models import OTPSMSToken
from notification.services.otp import verify_otp

from user.models import User, AuthSession

from .session import create_auth_session


class InactiveUserError(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("حساب کاربری غیرفعال است.")
    default_code = "invalid_otp"


class InvalidLogoutToken(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("توکن خروج معتبر نیست.")
    default_code = "invalid_logout_token"



@transaction.atomic
def login_with_otp(
    *,
    user:User,
    raw_code: str,
    request: Request
) -> dict[str, str]:
    user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )
    if not user.is_active:
        raise InactiveUserError
    verify_otp(
        user=user,
        raw_code=raw_code,
        reason=OTPSMSToken.OTPREASON.LOGIN,
    )
    if not user.is_mobile_verified:
        user.is_mobile_verified = True
        user.full_clean()
        user.save(
            update_fields=[
                "is_mobile_verified",
                "date_updated",
            ]
        )

    refresh = RefreshToken.for_user(user)

    session = create_auth_session(user=user, request=request)
    refresh['sid'] = str(session.id)

    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }

@transaction.atomic
def logout_session(
    *,
    raw_refresh: str,
) -> None:
    try:
        refresh = RefreshToken(raw_refresh)
    except TokenError as exc:
        raise InvalidLogoutToken from exc

    session_id = refresh.get("sid")
    user_id = refresh.get(api_settings.USER_ID_CLAIM)

    if not session_id or not user_id:
        raise InvalidLogoutToken

    try:
        session_uuid = UUID(str(session_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidLogoutToken from exc

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
        raise InvalidLogoutToken

    refresh.blacklist()

    session.revoked_at = timezone.now()
    session.save(
        update_fields=["revoked_at"]
    )