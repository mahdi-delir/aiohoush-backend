from django.core.cache import caches
from django.core.exceptions import ValidationError
from django.utils.crypto import salted_hmac

from rest_framework.throttling import SimpleRateThrottle

from aiohoush.core.client_ip import get_client_ip
from aiohoush.utilities.normalizers import normalize_mobile_to_09

throttle_cache = caches["throttling"]


class ClientIPMixin:
    """IP واقعی کاربر به‌جای get_ident پیش‌فرض DRF.

    get_ident پیش‌فرض (بدون NUM_PROXIES) کل هدر X-Forwarded-For را
    شناسه می‌گیرد؛ کاربر با تغییر این هدر محدودیت را دور می‌زند.
    """

    def get_ident(self, request):
        return get_client_ip(request) or "unknown"


class MobileKeyMixin:
    """کلید throttle بر اساس شمارهٔ موبایلِ نرمال‌شده.

    بدون نرمال‌سازی، 0912... و +98912... و ارقام فارسی کلیدهای
    متفاوت می‌ساختند و محدودیت هر شماره دور زده می‌شد.
    """

    key_salt = ""

    def get_cache_key(self, request, view):
        mobile = request.data.get("mobile")

        if not isinstance(mobile, str) or not mobile:
            return None

        try:
            mobile = normalize_mobile_to_09(mobile)
        except ValidationError:
            # شمارهٔ نامعتبر را serializer رد می‌کند؛ محدودیت IP
            # همچنان اعمال می‌شود.
            return None

        # شماره موبایل را مستقیماً داخل cache key ذخیره نمی‌کنیم.
        ident = salted_hmac(
            key_salt=self.key_salt,
            value=mobile,
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class IPKeyMixin(ClientIPMixin):
    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class OTPMobileRateThrottle(MobileKeyMixin, SimpleRateThrottle):
    scope = "otp_request_mobile"
    cache = throttle_cache
    key_salt = "otp-mobile-throttle"


class OTPIPRateThrottle(IPKeyMixin, SimpleRateThrottle):
    scope = "otp_request_ip"
    cache = throttle_cache


class OTPVerifyMobileRateThrottle(MobileKeyMixin, SimpleRateThrottle):
    scope = "otp_verify_mobile"
    cache = throttle_cache
    key_salt = "otp-verify-mobile-throttle"


class OTPVerifyIPRateThrottle(IPKeyMixin, SimpleRateThrottle):
    scope = "otp_verify_ip"
    cache = throttle_cache
