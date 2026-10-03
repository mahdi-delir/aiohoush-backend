import logging
from dataclasses import dataclass

from django.http import HttpRequest

from ipware import get_client_ip
from rest_framework.request import Request

from user.models import AuthSession, User
from user.tasks import enrich_auth_session


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

    session.full_clean()
    session.save()

    # تحلیل دستگاه بعد از ایجاد نشست انجام می‌شود
    try:
        enrich_auth_session.delay(
            session_id=str(session.id),
            user_agent=client_info.user_agent,
        )
    except Exception:
        # خراب‌بودن Celery نباید باعث شکست ورود کاربر شود
        logger.exception(
            "Could not enqueue device detection for session %s",
            session.id,
        )

    return session