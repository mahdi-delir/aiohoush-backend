from dataclasses import dataclass

from django.http import HttpRequest

from device_detector import DeviceDetector
from ipware import get_client_ip

from rest_framework.request import Request

from user.models import AuthSession, User

@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip_address: str | None
    user_agent: str

    browser_name: str
    browser_version: str

    os_name: str
    os_version: str

    device_type: str
    device_brand: str
    device_model: str


def get_client_info(request: HttpRequest) -> ClientInfo:
    ip_address, _ = get_client_ip(request)

    user_agent = request.headers.get(
        "User-Agent",
        "",
    )

    detector = DeviceDetector(user_agent).parse()

    return ClientInfo(
        ip_address=ip_address,
        user_agent=user_agent,

        browser_name=detector.client_name() or "",
        browser_version=detector.client_version() or "",

        os_name=detector.os_name() or "",
        os_version=detector.os_version() or "",

        device_type=detector.device_type() or "",
        device_brand=detector.device_brand() or "",
        device_model=detector.device_model() or "",
    )




def create_auth_session(
    *,
    user: User,
    request: Request,
) -> AuthSession:
    client_info = get_client_info(request)

    session = AuthSession(
        user=user,
        ip_address=client_info.ip_address,
        user_agent=client_info.user_agent,
        browser_name=client_info.browser_name,
        browser_version=client_info.browser_version,
        os_name=client_info.os_name,
        os_version=client_info.os_version,
        device_type=client_info.device_type,
        device_brand=client_info.device_brand,
        device_model=client_info.device_model,
    )

    session.full_clean()
    session.save()

    return session