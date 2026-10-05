"""شارژ آنلاین کیف پول از طریق ویدوپل.

مثل خرید محصولات AI: پارامترهای بازگشت از درگاه قابل جعل‌اند، پس
وضعیت واقعی از API ویدوپل استعلام و با سفارش تطبیق داده می‌شود.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounting.models import Payment, WalletEntry, WalletTopUp
from accounting.services.sales import credit_sale
from accounting.services.wallet import WalletError
from order.services import videopol


logger = logging.getLogger(__name__)

# کد محصول در ویدوپل؛ باید با تنظیمات ویدوپل یکی باشد.
TOP_UP_PRODUCT_CODE = "wallet-topup"


def start_top_up(*, user, amount_rial: int) -> WalletTopUp:
    minimum = settings.WALLET_TOPUP_MIN_RIAL
    maximum = settings.WALLET_TOPUP_MAX_RIAL

    if amount_rial < minimum or amount_rial > maximum:
        raise WalletError(
            f"مبلغ شارژ باید بین {minimum // 10:,} و {maximum // 10:,} تومان باشد."
        )

    # عمداً خارج از تراکنش: درخواست HTTP نباید تراکنش را باز نگه دارد.
    top_up = WalletTopUp.objects.create(
        user=user,
        amount_rial=amount_rial,
    )

    try:
        payment = videopol.create_payment(
            order_id=str(top_up.id),
            product_code=TOP_UP_PRODUCT_CODE,
            amount_rial=amount_rial,
            mobile=user.mobile,
            callback_url=settings.WALLET_TOPUP_CALLBACK_URL,
        )
    except videopol.VideopolError:
        logger.exception("Videopol top-up creation failed for %s", top_up.id)
        top_up.status = WalletTopUp.STATUS.FAILED
        top_up.save(update_fields=["status", "updated_at"])
        raise

    top_up.videopol_payment_id = payment.payment_id
    top_up.payment_url = payment.gateway_url
    top_up.save(
        update_fields=[
            "videopol_payment_id",
            "payment_url",
            "updated_at",
        ]
    )

    return top_up


@transaction.atomic
def apply_top_up_status(*, top_up_id, remote) -> str:
    """خروجی: "paid" یا "failed" یا "pending"."""
    top_up = (
        WalletTopUp.objects
        .select_for_update()
        .get(pk=top_up_id)
    )

    if top_up.status == WalletTopUp.STATUS.PAID:
        return "paid"

    if (
        remote.order_id != str(top_up.id)
        or remote.payment_id != top_up.videopol_payment_id
        or remote.product_code != TOP_UP_PRODUCT_CODE
        or remote.amount_rial != top_up.amount_rial
    ):
        logger.error(
            "Videopol payment %s does not match top-up %s",
            remote.payment_id,
            top_up.id,
        )
        return "failed"

    if remote.status == "success":
        now = timezone.now()

        top_up.status = WalletTopUp.STATUS.PAID
        top_up.reference_id = remote.reference_id
        top_up.paid_at = now
        top_up.save(
            update_fields=[
                "status",
                "reference_id",
                "paid_at",
                "updated_at",
            ]
        )

        payment = Payment.objects.create(
            user=top_up.user,
            created_by=top_up.user,
            top_up=top_up,
            amount=top_up.amount_rial,
            paid_at=now,
            tracking_code=top_up.reference_id or top_up.videopol_payment_id,
            gateway=Payment.GATEWAY.ZIBAL,
            status=Payment.STATUS.CONFIRMED,
            reviewed_at=now,
        )

        WalletEntry.objects.create(
            user=top_up.user,
            direction=WalletEntry.DIRECTION.CREDIT,
            amount=top_up.amount_rial,
            kind=WalletEntry.KIND.DEPOSIT,
            title="شارژ آنلاین کیف پول",
            payment=payment,
            top_up=top_up,
        )
        credit_sale(payment)
        return "paid"

    if remote.status in {"failed", "canceled"}:
        if top_up.status == WalletTopUp.STATUS.PENDING:
            top_up.status = (
                WalletTopUp.STATUS.CANCELLED
                if remote.status == "canceled"
                else WalletTopUp.STATUS.FAILED
            )
            top_up.save(update_fields=["status", "updated_at"])
        return "failed"

    return "pending"
