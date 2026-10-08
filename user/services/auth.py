from dataclasses import dataclass
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
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from notification.models import OTPSMSToken
from notification.services.otp import verify_otp

from user.models import User, AuthSession

from .devices import (
    active_sessions,
    drop_ticket,
    has_free_device_slot,
    issue_ticket,
    ticket_user_id,
)
from .session import create_auth_session


class InactiveUserError(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("حساب کاربری غیرفعال است.")
    default_code = "invalid_otp"


class InvalidLogoutToken(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("توکن خروج معتبر نیست.")
    default_code = "invalid_logout_token"

class AuthSessionNotFound(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("نشست موردنظر یافت نشد.")
    default_code = "session_not_found"


class DeviceTicketExpired(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _("مهلت انتخاب دستگاه تمام شد؛ لطفاً دوباره وارد شوید.")
    default_code = "device_ticket_expired"


@dataclass(frozen=True)
class LoginResult:
    tokens: dict[str, str] | None = None
    ticket: str | None = None


class CannotRevokeCurrentSession(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _(
        "برای خروج از همین دستگاه از گزینهٔ خروج استفاده کنید."
    )
    default_code = "cannot_revoke_current_session"


@transaction.atomic
def login_with_otp(
    *,
    user:User,
    raw_code: str,
    request: Request
) -> LoginResult:
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

    if not has_free_device_slot(user):
        return LoginResult(ticket=issue_ticket(user))

    return LoginResult(tokens=issue_tokens(user=user, request=request))


def issue_tokens(*, user: User, request: Request) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    session = create_auth_session(user=user, request=request, refresh_jti=refresh[api_settings.JTI_CLAIM])
    refresh['sid'] = str(session.id)

    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }


@transaction.atomic
def free_device_and_login(
    *,
    ticket: str,
    request: Request,
    session_id: UUID | None = None,
    revoke_all: bool = False,
) -> LoginResult:
    user_id = ticket_user_id(ticket)
    if user_id is None:
        raise DeviceTicketExpired

    user = (
        User.objects
        .select_for_update()
        .filter(pk=user_id)
        .first()
    )
    if user is None:
        raise DeviceTicketExpired
    if not user.is_active:
        raise InactiveUserError

    if revoke_all:
        logout_all_sessions(user=user)
    elif session_id is not None:
        session = (
            AuthSession.objects
            .select_for_update()
            .filter(
                id=session_id,
                user=user,
                revoked_at__isnull=True,
            )
            .first()
        )
        if session is not None:
            _revoke_session(user=user, session=session)

    if not has_free_device_slot(user):
        return LoginResult(ticket=ticket)

    transaction.on_commit(lambda: drop_ticket(ticket))
    return LoginResult(tokens=issue_tokens(user=user, request=request))


def device_limit_sessions(ticket: str):
    user_id = ticket_user_id(ticket)
    if user_id is None:
        raise DeviceTicketExpired
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise DeviceTicketExpired
    return user, active_sessions(user)

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

@transaction.atomic
def logout_all_sessions(
     *,
    user: User,
) -> None:
    now = timezone.now()

    user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )

    active_sessions = list(
        AuthSession.objects
        .select_for_update()
        .filter(
            user=user,
            revoked_at__isnull=True,
        )
    )

    if active_sessions:
        AuthSession.objects.filter(
            pk__in=[
                session.pk
                for session in active_sessions
            ]
        ).update(
            revoked_at=now
        )

    outstanding_tokens = list(
        OutstandingToken.objects
        .select_for_update()
        .filter(
            user=user,
            expires_at__gt=now,
        )
    )

    if outstanding_tokens:
        BlacklistedToken.objects.bulk_create(
            [
                BlacklistedToken(token=token)
                for token in outstanding_tokens
            ],
            ignore_conflicts=True,
        )

@transaction.atomic
def revoke_other_session(
    *,
    user: User,
    current_session_id: str | None,
    target_session_id: UUID,
) -> None:
    # نشست فعلی باید با logout بسته شود تا BFF هم کوکی و
    # Redis را پاک کند؛ وگرنه کاربر با نشستی نیمه‌باطل می‌ماند.
    if (
        current_session_id
        and str(current_session_id) == str(target_session_id)
    ):
        raise CannotRevokeCurrentSession

    session = (
        AuthSession.objects
        .select_for_update()
        .filter(
            id=target_session_id,
            user=user,
            revoked_at__isnull=True,
        )
        .first()
    )

    if session is None:
        raise AuthSessionNotFound

    _revoke_session(user=user, session=session)


def _revoke_session(*, user: User, session: AuthSession) -> None:
    if session.refresh_jti:
        outstanding_token = (
            OutstandingToken.objects
            .select_for_update()
            .filter(
                user=user,
                jti=session.refresh_jti,
            )
            .first()
        )

        if outstanding_token is not None:
            BlacklistedToken.objects.get_or_create(
                token=outstanding_token
            )

    session.revoked_at = timezone.now()

    session.save(
        update_fields=[
            "revoked_at",
        ]
    )