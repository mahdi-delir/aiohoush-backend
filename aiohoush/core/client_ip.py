"""تشخیص IP واقعی کاربر.

ترتیب اعتماد:
1. درخواستی که از BFF (Next.js) آمده و کلید مشترک درست دارد:
   IP از هدر X-Aiohoush-Client-IP خوانده می‌شود.
2. اگر CLIENT_IP_META_KEY تنظیم شده باشد:
   - HTTP_X_REAL_IP: وقتی proxy جلوی جنگو این هدر را بازنویسی می‌کند.
   - HTTP_X_FORWARDED_FOR: از انتهای هدر به اندازهٔ
     TRUSTED_PROXY_COUNT شمرده می‌شود (ابتدای هدر قابل جعل است).
3. در غیر این صورت REMOTE_ADDR.

هیچ‌وقت به ابتدای X-Forwarded-For اعتماد نمی‌کنیم، چون کاربر
می‌تواند آن را جعل کند.
"""

import ipaddress
import secrets

from django.conf import settings


BFF_TOKEN_META_KEY = "HTTP_X_AIOHOUSH_BFF_TOKEN"
BFF_CLIENT_IP_META_KEY = "HTTP_X_AIOHOUSH_CLIENT_IP"


def _valid_ip(value) -> str | None:
    if not value or not isinstance(value, str):
        return None

    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _is_trusted_bff(meta) -> bool:
    expected = settings.BFF_SHARED_SECRET

    if not expected:
        return False

    provided = meta.get(BFF_TOKEN_META_KEY, "")

    return secrets.compare_digest(
        provided.encode(),
        expected.encode(),
    )


def get_client_ip(request) -> str | None:
    # DRF Request یا Django HttpRequest
    meta = getattr(request, "META", None)

    if meta is None:
        meta = request._request.META

    if _is_trusted_bff(meta):
        ip = _valid_ip(meta.get(BFF_CLIENT_IP_META_KEY))
        if ip:
            return ip

    meta_key = settings.CLIENT_IP_META_KEY

    if meta_key == "HTTP_X_FORWARDED_FOR":
        hops = meta.get(meta_key, "").split(",")
        index = len(hops) - settings.TRUSTED_PROXY_COUNT
        ip = _valid_ip(hops[index]) if index >= 0 else None
        if ip:
            return ip

    elif meta_key:
        ip = _valid_ip(meta.get(meta_key))
        if ip:
            return ip

    return _valid_ip(meta.get("REMOTE_ADDR"))
