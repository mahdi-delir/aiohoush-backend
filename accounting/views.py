import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse

from accounting.models import Payment, WalletEntry, WalletTopUp
from accounting.services import topup as topup_service
from accounting.services.wallet import WalletError, get_balance
from order.services import videopol


logger = logging.getLogger(__name__)


WALLET_HISTORY_LIMIT = 100

GATEWAY_TYPES = {
    Payment.GATEWAY.ZIBAL: "online",
    Payment.GATEWAY.ZARINPAL: "online",
    Payment.GATEWAY.TRANSFER: "transfer",
}


def _payment_fields(payment: Payment | None) -> dict:
    if payment is None:
        return {
            "gate": None,
            "tracking_code": None,
            "card_last4": None,
        }

    return {
        "gate": GATEWAY_TYPES.get(payment.gateway),
        "tracking_code": payment.tracking_code or None,
        "card_last4": payment.user_card_digits or None,
    }


def _entry_row(entry: WalletEntry) -> dict:
    return {
        "id": f"entry-{entry.pk}",
        "side": (
            "deposit"
            if entry.direction == WalletEntry.DIRECTION.CREDIT
            else "withdraw"
        ),
        "kind": entry.kind,
        "title": entry.title,
        "description": entry.description or None,
        "date": entry.created_at.isoformat(),
        "amount": entry.amount,
        "status": "confirmed",
        **_payment_fields(entry.payment),
    }


def _payment_row(payment: Payment) -> dict:
    """پرداختی که هنوز تأیید نشده یا رد شده؛ در موجودی حساب نمی‌شود."""
    return {
        "id": f"payment-{payment.pk}",
        "side": "deposit",
        "kind": "deposit",
        "title": (
            "واریز با انتقال وجه"
            if payment.gateway == Payment.GATEWAY.TRANSFER
            else "پرداخت آنلاین"
        ),
        "description": None,
        "date": (payment.created_at or payment.paid_at).isoformat(),
        "amount": int(payment.amount),
        "status": payment.status,
        **_payment_fields(payment),
    }


class WalletView(APIView):
    """موجودی و تاریخچهٔ کیف پول کاربر فعلی (برای همهٔ نقش‌ها)."""

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        user = request.user

        entries = list(
            WalletEntry.objects
            .filter(user=user)
            .select_related("payment")
            .order_by("-created_at", "-id")[:WALLET_HISTORY_LIMIT]
        )

        open_payments = list(
            Payment.objects
            .filter(
                user=user,
                is_deleted=False,
                status__in=[
                    Payment.STATUS.PENDING,
                    Payment.STATUS.REJECTED,
                ],
            )
            .order_by("-id")[:WALLET_HISTORY_LIMIT]
        )

        rows = [_entry_row(entry) for entry in entries]
        rows += [_payment_row(payment) for payment in open_payments]
        rows.sort(key=lambda row: row["date"], reverse=True)

        pending_total = sum(
            int(payment.amount)
            for payment in open_payments
            if payment.status == Payment.STATUS.PENDING
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="اطلاعات کیف پول دریافت شد.",
            data={
                # همهٔ مبالغ به ریال؛ تبدیل به تومان در فرانت انجام می‌شود.
                "currency": "IRR",
                "balance": get_balance(user),
                "pending_deposits": pending_total,
                "transactions": rows[:WALLET_HISTORY_LIMIT],
            },
            status=status.HTTP_200_OK,
        )


class WalletTopUpView(APIView):
    """شروع شارژ آنلاین؛ آدرس درگاه را برمی‌گرداند."""

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        try:
            amount_rial = int(request.data.get("amount_rial"))
        except (TypeError, ValueError):
            return APIResponse(
                success=False,
                called_by="webapp",
                message="مبلغ شارژ معتبر نیست.",
                status=status.HTTP_200_OK,
            )

        try:
            top_up = topup_service.start_top_up(
                user=request.user,
                amount_rial=amount_rial,
            )
        except WalletError as exc:
            return APIResponse(
                success=False,
                called_by="webapp",
                message=str(exc),
                status=status.HTTP_200_OK,
            )
        except videopol.VideopolError:
            # مشکل واقعی در ارتباط با درگاه
            return APIResponse(
                success=False,
                called_by="webapp",
                message="ایجاد پرداخت ناموفق بود. لطفاً دوباره تلاش کنید.",
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="درخواست پرداخت ایجاد شد.",
            data={
                "top_up_id": str(top_up.id),
                "payment_url": top_up.payment_url,
            },
            status=status.HTTP_200_OK,
        )


class WalletTopUpReturnView(APIView):
    """بازگشت کاربر از ویدوپل؛ وضعیت واقعی استعلام می‌شود."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        payment_id = str(
            request.query_params.get("payment_id", "")
        ).strip()

        if not payment_id.isdigit():
            return self._redirect("failed")

        top_up = (
            WalletTopUp.objects
            .filter(videopol_payment_id=payment_id)
            .only("id", "status")
            .first()
        )

        if top_up is None:
            logger.warning(
                "Top-up return for unknown videopol payment %s",
                payment_id,
            )
            return self._redirect("failed")

        if top_up.status == WalletTopUp.STATUS.PAID:
            return self._redirect("paid")

        try:
            remote = videopol.get_payment_status(payment_id)
        except videopol.VideopolError:
            logger.exception(
                "Videopol status lookup failed for top-up %s",
                top_up.id,
            )
            return self._redirect("pending")

        result = topup_service.apply_top_up_status(
            top_up_id=top_up.id,
            remote=remote,
        )

        return self._redirect(result)

    @staticmethod
    def _redirect(result):
        query = urlencode({"payment": result})
        return HttpResponseRedirect(
            f"{settings.WALLET_TOPUP_RESULT_URL}?{query}"
        )


class MentorLeaderboardView(APIView):
    """برترین منتورهای دورهٔ جاری (فقط امتیاز، بدون مبلغ فروش)."""

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        from accounting.services.leaderboard import build_leaderboard

        return APIResponse(
            success=True,
            called_by="webapp",
            message="رتبه‌بندی منتورها دریافت شد.",
            data=build_leaderboard(request),
            status=status.HTTP_200_OK,
        )
