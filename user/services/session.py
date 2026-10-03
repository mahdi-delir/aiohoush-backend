import logging
from dataclasses import dataclass

from django.http import HttpRequest

from ipware import get_client_ip
from rest_framework.request import Request

from user.models import AuthSession, User
from user.tasks import enrich_auth_session
from django.db import transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip_address: str | None
    user_agent: str


def get_client_info(request: HttpRequest) -> ClientInfo:
    ip_address, _ = get_client_ip(request)

    user_agent = request.headers.get(
        "User-Agent",
        "",
    )

    return ClientInfo(
        ip_address=ip_address,
        user_agent=user_agent[:1000],
    )


def create_auth_session(
    *,
    user: User,
    request: Request,
    refresh_jti: str,
) -> AuthSession:
    client_info = get_client_info(request)

    # ساخت نشست بدون تحلیل سنگین User-Agent
    session = AuthSession(
        user=user,
        refresh_jti=refresh_jti,
        ip_address=client_info.ip_address,
        user_agent=client_info.user_agent,
        browser_name="",
        browser_version="",
        os_name="",
        os_version="",
        device_type="",
        device_brand="",
        device_model="",
    )
    logger.warning("AUTH: before session save")

    session.full_clean()
    session.save()
    logger.warning(
    "AUTH: session saved %s",
    session.id,
)

    # تحلیل دستگاه بعد از ایجاد نشست انجام می‌شود
    def enqueue_device_detection(
        *,
        session_id: str,
        user_agent: str,
    ) -> None:
        logger.warning(
        "AUTH: enqueue started %s",
        session_id,
    )
        try:
            enrich_auth_session.delay(
                session_id=session_id,
                user_agent=user_agent,
            )
            logger.warning(
            "AUTH: enqueue finished %s",
            session_id,
        )
        except Exception:
            logger.exception(
                "Could not enqueue device detection for session %s",
                session_id,
            )


    transaction.on_commit(
        lambda session_id=str(session.id),
        user_agent=client_info.user_agent: enqueue_device_detection(
            session_id=session_id,
            user_agent=user_agent,
        )
    )
    logger.warning(
    "AUTH: on_commit registered %s",
    session.id,
)

    return session