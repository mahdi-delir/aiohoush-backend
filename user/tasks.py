import logging

from celery import shared_task
from django.db import close_old_connections

from device_detector import DeviceDetector

from user.models import AuthSession


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    soft_time_limit=30,
    time_limit=45,
    ignore_result=True,
)
def enrich_auth_session(
    self,
    session_id: str,
    user_agent: str,
):
    close_old_connections()

    try:
        detector = DeviceDetector(user_agent).parse()

        AuthSession.objects.filter(
            id=session_id,
        ).update(
            browser_name=detector.client_name() or "",
            browser_version=detector.client_version() or "",
            os_name=detector.os_name() or "",
            os_version=detector.os_version() or "",
            device_type=detector.device_type() or "",
            device_brand=detector.device_brand() or "",
            device_model=detector.device_model() or "",
        )

    except AuthSession.DoesNotExist:
        logger.warning(
            "Auth session %s no longer exists",
            session_id,
        )

    except Exception:
        logger.exception(
            "Could not detect device for auth session %s",
            session_id,
        )

    finally:
        close_old_connections()