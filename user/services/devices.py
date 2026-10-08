import hashlib
import secrets

from django.core.cache import cache
from django.db.models import Exists, OuterRef
from django.utils import timezone

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from user.models import AuthSession


TICKET_TTL_SECONDS = 600
MAX_TICKET_LENGTH = 200


def active_sessions(user):
    live_token = OutstandingToken.objects.filter(
        user=user,
        jti=OuterRef("refresh_jti"),
        expires_at__gt=timezone.now(),
        blacklistedtoken__isnull=True,
    )

    return (
        AuthSession.objects
        .filter(
            user=user,
            revoked_at__isnull=True,
        )
        .filter(Exists(live_token))
        .order_by("-created_at")
    )


def has_free_device_slot(user) -> bool:
    return active_sessions(user).count() < user.max_devices


def _ticket_key(ticket: str) -> str:
    digest = hashlib.sha256(ticket.encode()).hexdigest()
    return f"auth:device-ticket:{digest}"


def issue_ticket(user) -> str:
    ticket = secrets.token_urlsafe(32)
    cache.set(_ticket_key(ticket), user.pk, TICKET_TTL_SECONDS)
    return ticket


def ticket_user_id(ticket) -> int | None:
    if not isinstance(ticket, str) or not ticket or len(ticket) > MAX_TICKET_LENGTH:
        return None
    return cache.get(_ticket_key(ticket))


def drop_ticket(ticket: str) -> None:
    cache.delete(_ticket_key(ticket))
