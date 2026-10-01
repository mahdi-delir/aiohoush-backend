from django.utils.crypto import salted_hmac
from django.core.cache import caches
from django.utils.crypto import salted_hmac

from rest_framework.throttling import SimpleRateThrottle

throttle_cache = caches["throttling"]

class OTPMobileRateThrottle(SimpleRateThrottle):
    scope = "otp_request_mobile"
    cache = throttle_cache


    def get_cache_key(self, request, view):
        mobile = request.data.get("mobile")

        if not isinstance(mobile, str) or not mobile:
            return None

        # شماره موبایل را مستقیماً داخل cache key ذخیره نمی‌کنیم.
        ident = salted_hmac(
            key_salt="otp-mobile-throttle",
            value=mobile,
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class OTPIPRateThrottle(SimpleRateThrottle):
    scope = "otp_request_ip"
    cache = throttle_cache

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }

class OTPVerifyMobileRateThrottle(SimpleRateThrottle):
    scope = "otp_verify_mobile"
    cache = throttle_cache

    def get_cache_key(self, request, view):
        mobile = request.data.get("mobile")

        if not isinstance(mobile, str) or not mobile:
            return None

        ident = salted_hmac(
            key_salt="otp-verify-mobile-throttle",
            value=mobile,
        ).hexdigest()

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }

class OTPVerifyIPRateThrottle(SimpleRateThrottle):
    scope = "otp_verify_ip"
    cache = throttle_cache

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }