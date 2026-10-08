import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q

from notification.models import SMSServerResponse


logger = logging.getLogger(__name__)

NO_CREDIT_ERROR_CODE = 19
FAILURE_STREAK_LIMIT = 5
STATE_TIMEOUT = 60 * 60 * 24 * 30
ADMIN_GROUP = "مدیر اصلی"

FAILURES_KEY = "sms-alert:failures"
NO_CREDIT_ALERTED_KEY = "sms-alert:no-credit"
STREAK_ALERTED_KEY = "sms-alert:streak"

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def record_sms_result(*, status: str, body) -> None:
    try:
        _record(status=status, body=body)
    except Exception:
        logger.exception("Could not record SMS health state.")


def _record(*, status: str, body) -> None:
    if status == SMSServerResponse.SMSSTATUS.SENT:
        cache.delete_many([FAILURES_KEY, NO_CREDIT_ALERTED_KEY, STREAK_ALERTED_KEY])
        return

    cache.add(FAILURES_KEY, 0, STATE_TIMEOUT)
    failures = cache.incr(FAILURES_KEY)

    error_code = body.get("ErrorCode") if isinstance(body, dict) else None
    error_text = body.get("Error") if isinstance(body, dict) else None

    if error_code == NO_CREDIT_ERROR_CODE and cache.add(NO_CREDIT_ALERTED_KEY, 1, STATE_TIMEOUT):
        notify_admins(
            title="اعتبار سامانه پیامک تمام شده است",
            body=(
                "سامانه پیامک پاسخ «اعتبار حساب کافی نیست» داد. "
                "تا حساب شارژ نشود، کد ورود و سایر پیامک‌ها برای کاربران ارسال نمی‌شود."
            ),
        )

    if failures >= FAILURE_STREAK_LIMIT and cache.add(STREAK_ALERTED_KEY, 1, STATE_TIMEOUT):
        reason = error_text or "خطای ارتباط با سامانه پیامک"
        count = str(FAILURE_STREAK_LIMIT).translate(PERSIAN_DIGITS)
        notify_admins(
            title=f"{count} پیامک پشت سر هم ارسال نشد",
            body=(
                f"{count} پیامک آخر ارسال نشده‌اند. "
                f"آخرین خطا: {reason}. "
                "سامانه پیامک و لاگ‌ها را بررسی کنید."
            ),
        )


def admin_users():
    User = get_user_model()
    return (
        User.objects
        .filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name=ADMIN_GROUP))
        .distinct()
    )


def notify_admins(*, title: str, body: str) -> None:
    from announcement.models import Announcement
    from announcement.services.announcements import publish

    recipients = list(admin_users())
    sender = next((user for user in recipients if user.is_superuser), None)

    if not recipients or sender is None:
        logger.error("SMS alert not delivered, no admin to notify: %s", title)
        return

    announcement = Announcement.objects.create(
        title=title,
        body=body,
        audience=Announcement.AUDIENCE.USERS,
        created_by=sender,
    )
    announcement.users.set(recipients)
    publish(announcement)
