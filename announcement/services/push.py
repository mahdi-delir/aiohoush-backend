"""Web Push: نوتیفیکیشن روی گوشی و دسکتاپ، حتی وقتی اپ بسته است.

پیام از سرویس push خود مرورگر عبور می‌کند (گوگل برای کروم/اندروید، اپل
برای سافاری/آیفون، موزیلا برای فایرفاکس) و با کلیدهای همان مرورگر
رمزنگاری می‌شود. روی آیفون فقط برای اپ نصب‌شده روی صفحهٔ اصلی (iOS 16.4+).
"""

import json
import logging
import re

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from announcement.models import PushSubscription


logger = logging.getLogger(__name__)

# اشتراک بعد از این تعداد خطای پشت‌سرهم حذف می‌شود.
MAX_FAILURES = 5
PUSH_TTL_SECONDS = 24 * 60 * 60
PUSH_TIMEOUT_SECONDS = 10

_B64URL = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class PushError(Exception):
    """خطای قابل‌نمایش به کاربر."""


def is_enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def subscribe(*, user, endpoint: str, p256dh: str, auth: str, user_agent: str = "") -> PushSubscription:
    endpoint = (endpoint or "").strip()
    if not endpoint.startswith("https://") or len(endpoint) > 1000:
        raise PushError("اشتراک نامعتبر است.")
    for value, max_length in ((p256dh, 200), (auth, 100)):
        if not value or len(value) > max_length or not _B64URL.match(value):
            raise PushError("اشتراک نامعتبر است.")

    # اگر همین دستگاه قبلاً با حساب دیگری ثبت شده بود، به کاربر فعلی منتقل می‌شود.
    subscription, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": (user_agent or "")[:300],
            "failure_count": 0,
        },
    )
    return subscription


def unsubscribe(*, user, endpoint: str) -> None:
    PushSubscription.objects.filter(user=user, endpoint=(endpoint or "").strip()).delete()


def _send_one(subscription: PushSubscription, payload: str) -> bool:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=PUSH_TTL_SECONDS,
            timeout=PUSH_TIMEOUT_SECONDS,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            # کاربر اجازه را برداشته یا اپ را پاک کرده؛ این اشتراک دیگر کار نمی‌کند.
            subscription.delete()
            return False
        _record_failure(subscription, f"status={status}")
        return False
    except Exception as exc:  # خطای شبکه و ...
        _record_failure(subscription, exc.__class__.__name__)
        return False

    PushSubscription.objects.filter(pk=subscription.pk).update(
        last_success_at=timezone.now(), failure_count=0,
    )
    return True


def _record_failure(subscription: PushSubscription, reason: str) -> None:
    PushSubscription.objects.filter(pk=subscription.pk).update(failure_count=F("failure_count") + 1)
    PushSubscription.objects.filter(pk=subscription.pk, failure_count__gte=MAX_FAILURES).delete()
    logger.warning("Push failed. subscription=%s reason=%s", subscription.pk, reason)


def send_to_users(*, user_ids, title: str, body: str, url: str, tag: str) -> tuple[int, int]:
    """(تعداد موفق، تعداد کل) را برمی‌گرداند."""
    if not is_enabled():
        return 0, 0

    payload = json.dumps(
        {"title": title, "body": body, "url": url, "tag": tag},
        ensure_ascii=False,
    )

    sent = total = 0
    for subscription in PushSubscription.objects.filter(user_id__in=user_ids).iterator(chunk_size=500):
        total += 1
        sent += _send_one(subscription, payload)
    return sent, total
