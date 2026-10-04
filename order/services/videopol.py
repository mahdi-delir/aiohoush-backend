"""کلاینت API پرداخت خارجی ویدوپل.

قرارداد سمت ویدوپل (payments/views.py):
- POST {VIDEOPOL_API_URL}/api/payments/external/
  ساخت پرداخت؛ پاسخ: success, payment_id, status, gateway_url
- POST {VIDEOPOL_API_URL}/api/payments/external/<payment_id>/verify/
  استعلام وضعیت؛ پاسخ: success, payment_id, order_id, product_code,
  amount_rial, status (created/pending/success/failed/canceled),
  reference_id, paid_at
- بعد از درگاه، مرورگر کاربر به callback_url با
  ?payment_id=..&status=paid|failed|pending برمی‌گردد. این پارامترها
  قابل جعل‌اند؛ وضعیت واقعی فقط از endpoint استعلام خوانده می‌شود.

هر دو endpoint هم هدر X-AIOHOUSH-API-KEY و هم Authorization: Bearer
را بررسی می‌کنند.
"""

from dataclasses import dataclass

import requests
from django.conf import settings


class VideopolError(Exception):
    """خطای ارتباط با ویدوپل یا پاسخ نامعتبر."""


@dataclass(frozen=True, slots=True)
class CreatedPayment:
    payment_id: str
    gateway_url: str


@dataclass(frozen=True, slots=True)
class PaymentStatus:
    payment_id: str
    order_id: str
    product_code: str
    amount_rial: int
    status: str
    reference_id: str


def _url(path: str) -> str:
    return f"{settings.VIDEOPOL_API_URL.rstrip('/')}{path}"


def _headers(*, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.VIDEOPOL_API_KEY}",
        "X-AIOHOUSH-API-KEY": settings.VIDEOPOL_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _json(response: requests.Response) -> dict:
    try:
        body = response.json()
    except ValueError as exc:
        raise VideopolError(
            f"Invalid JSON from videopol (HTTP {response.status_code})"
        ) from exc

    if not isinstance(body, dict):
        raise VideopolError("Unexpected response shape from videopol")

    return body


def create_payment(
    *,
    order_id: str,
    product_code: str,
    amount_rial: int,
    mobile: str,
    callback_url: str,
) -> CreatedPayment:
    try:
        response = requests.post(
            _url("/api/payments/external/"),
            json={
                "order_id": order_id,
                "product_code": product_code,
                "amount_rial": amount_rial,
                "mobile": mobile,
                "callback_url": callback_url,
            },
            headers=_headers(idempotency_key=order_id),
            timeout=settings.VIDEOPOL_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise VideopolError("Videopol is unreachable") from exc

    body = _json(response)

    if (
        not response.ok
        or not body.get("success")
        or body.get("status") != "pending"
        or not body.get("gateway_url")
        or not body.get("payment_id")
    ):
        raise VideopolError(
            body.get("message")
            or f"Payment creation rejected (HTTP {response.status_code})"
        )

    return CreatedPayment(
        payment_id=str(body["payment_id"]),
        gateway_url=str(body["gateway_url"]),
    )


def get_payment_status(payment_id: str) -> PaymentStatus:
    try:
        response = requests.post(
            _url(f"/api/payments/external/{int(payment_id)}/verify/"),
            headers=_headers(),
            timeout=settings.VIDEOPOL_TIMEOUT_SECONDS,
        )
    except (TypeError, ValueError) as exc:
        raise VideopolError("Invalid payment id") from exc
    except requests.RequestException as exc:
        raise VideopolError("Videopol is unreachable") from exc

    body = _json(response)

    if not response.ok or not body.get("success"):
        raise VideopolError(
            f"Payment status lookup failed (HTTP {response.status_code})"
        )

    try:
        return PaymentStatus(
            payment_id=str(body["payment_id"]),
            order_id=str(body["order_id"]),
            product_code=str(body["product_code"]),
            amount_rial=int(body["amount_rial"]),
            status=str(body["status"]),
            reference_id=str(body.get("reference_id") or ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise VideopolError("Incomplete payment status from videopol") from exc
