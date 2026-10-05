from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, status
from rest_framework.views import exception_handler


# خطاهایی که «مدیریت‌شده» حساب می‌شوند: ورودی نامعتبر، نبود دسترسی،
# پیدا نشدن، محدودیت درخواست. قرارداد پروژه: این‌ها با HTTP 200 و
# success=false برمی‌گردند تا هر status غیر 200 یعنی مشکل واقعی.
HANDLED_EXCEPTIONS = (
    exceptions.ValidationError,
    exceptions.ParseError,
    exceptions.PermissionDenied,
    exceptions.NotFound,
    exceptions.Throttled,
    DjangoPermissionDenied,
    Http404,
)

# خطاهای احراز هویت عمداً status واقعی (401/403) را نگه می‌دارند:
# BFF با 401 توکن را refresh می‌کند و با 4xx در refresh نشست را پاک
# می‌کند. NotAuthenticated و AuthenticationFailed زیرکلاس
# PermissionDenied نیستند، پس اینجا تبدیل نمی‌شوند.
AUTH_EXCEPTIONS = (
    exceptions.NotAuthenticated,
    exceptions.AuthenticationFailed,
)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    original_data = response.data
    message = _("درخواست نامعتبر است.")
    if (
        isinstance(original_data, dict)
        and isinstance(original_data.get("detail"), str)
    ):
        message = original_data["detail"]
    elif isinstance(exc, exceptions.ValidationError):
        message = _first_message(original_data) or message

    if (
        isinstance(exc, HANDLED_EXCEPTIONS)
        and not isinstance(exc, AUTH_EXCEPTIONS)
    ):
        response.status_code = status.HTTP_200_OK
        # Retry-After برای Throttled در هدر می‌ماند.

    response.data = {
        "success": False,
        "message": message,
        "called_by": 'webapp',
        "detail": original_data,
    }
    return response


def _first_message(errors):
    """اولین پیام خطای اعتبارسنجی برای نمایش به کاربر."""
    if isinstance(errors, dict):
        for value in errors.values():
            message = _first_message(value)
            if message:
                return message
    elif isinstance(errors, (list, tuple)):
        for value in errors:
            message = _first_message(value)
            if message:
                return message
    elif errors:
        return str(errors)
    return None
