"""دفتر کیف پول.

همهٔ اسناد کیف پول فقط از طریق این ماژول ثبت می‌شوند. اسناد ویرایش یا
حذف نمی‌شوند؛ برای اصلاح، سند معکوس ثبت می‌شود.

مبالغ همه به ریال هستند.
"""

from django.db import transaction
from django.db.models import BigIntegerField, Case, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounting.models import Payment, WalletEntry


class WalletError(Exception):
    """خطای قابل‌نمایش به کاربر."""


def get_balance(user) -> int:
    # output_field صریح: amount مثبت است ولی جمع علامت‌دار منفی هم می‌شود.
    signed = Case(
        When(direction=WalletEntry.DIRECTION.CREDIT, then=F("amount")),
        default=-F("amount"),
        output_field=BigIntegerField(),
    )

    return int(
        WalletEntry.objects
        .filter(user=user)
        .aggregate(
            balance=Coalesce(
                Sum(signed),
                Value(0),
                output_field=BigIntegerField(),
            )
        )["balance"]
    )


def _payment_title(payment: Payment) -> str:
    if payment.gateway == Payment.GATEWAY.TRANSFER:
        return "واریز با انتقال وجه"
    return "پرداخت آنلاین"


# --- واریز -----------------------------------------------------------------

@transaction.atomic
def confirm_payment(*, payment_id: int, by) -> Payment:
    payment = (
        Payment.objects
        .select_for_update()
        .get(pk=payment_id)
    )

    if payment.is_deleted:
        raise WalletError("این پرداخت حذف شده است.")

    if payment.status != Payment.STATUS.PENDING:
        raise WalletError("فقط پرداخت در انتظار تأیید قابل تأیید است.")

    payment.status = Payment.STATUS.CONFIRMED
    payment.reviewed_by = by
    payment.reviewed_at = timezone.now()
    payment.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    WalletEntry.objects.create(
        user=payment.user,
        direction=WalletEntry.DIRECTION.CREDIT,
        amount=int(payment.amount),
        kind=WalletEntry.KIND.DEPOSIT,
        title=_payment_title(payment),
        created_by=by,
        payment=payment,
    )

    return payment


@transaction.atomic
def reject_payment(*, payment_id: int, by) -> Payment:
    payment = (
        Payment.objects
        .select_for_update()
        .get(pk=payment_id)
    )

    if payment.status != Payment.STATUS.PENDING:
        raise WalletError("فقط پرداخت در انتظار تأیید قابل رد است.")

    payment.status = Payment.STATUS.REJECTED
    payment.reviewed_by = by
    payment.reviewed_at = timezone.now()
    payment.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    return payment


# --- خرید دوره -------------------------------------------------------------

def order_total(order) -> int:
    """مبلغ نهایی سفارش = مجموع (قیمت − تخفیف) اقلام."""
    return int(
        sum(
            item.price - item.discount
            for item in order.requested_products.all()
        )
    )


def debit_course_order(*, order, by) -> WalletEntry | None:
    """سند خرید سفارش تأییدشده. باید داخل تراکنش تأیید سفارش صدا زده شود.

    موجودی منفی مجاز است؛ این‌که چه کسی اجازهٔ تأیید با موجودی ناکافی
    را دارد در لایهٔ تأیید سفارش کنترل می‌شود.
    """
    amount = order_total(order)

    # سفارش رایگان (مثلاً تخفیف کامل) سندی ندارد.
    if amount <= 0:
        return None

    titles = "، ".join(
        item.course.title
        for item in order.requested_products.select_related("course")
    )

    return WalletEntry.objects.create(
        user=order.student,
        direction=WalletEntry.DIRECTION.DEBIT,
        amount=amount,
        kind=WalletEntry.KIND.COURSE_PURCHASE,
        title=f"خرید دوره: {titles}"[:255],
        created_by=by,
        order=order,
    )


# --- محصولات AI ------------------------------------------------------------

def record_ai_purchase(*, ai_order, product_title: str) -> None:
    """پرداخت موفق درگاه: واریز (+) و خرید (−) با هم.

    باید داخل تراکنشی صدا زده شود که سفارش را قفل کرده است.
    دوباره صدا زدن آن اثری ندارد.
    """
    if hasattr(ai_order, "payment"):
        return

    payment = Payment.objects.create(
        user=ai_order.user,
        created_by=ai_order.user,
        ai_order=ai_order,
        amount=ai_order.amount_rial,
        paid_at=ai_order.paid_at or timezone.now(),
        tracking_code=ai_order.reference_id or ai_order.videopol_payment_id,
        gateway=Payment.GATEWAY.ZIBAL,
        status=Payment.STATUS.CONFIRMED,
        reviewed_at=timezone.now(),
    )

    WalletEntry.objects.create(
        user=ai_order.user,
        direction=WalletEntry.DIRECTION.CREDIT,
        amount=ai_order.amount_rial,
        kind=WalletEntry.KIND.DEPOSIT,
        title=_payment_title(payment),
        payment=payment,
        ai_order=ai_order,
    )

    WalletEntry.objects.create(
        user=ai_order.user,
        direction=WalletEntry.DIRECTION.DEBIT,
        amount=ai_order.amount_rial,
        kind=WalletEntry.KIND.AI_PURCHASE,
        title=f"خرید {product_title}"[:255],
        payment=payment,
        ai_order=ai_order,
    )


# --- سند معکوس (برای مرجوعی، بخشودگی و اصلاح در فازهای بعد) ----------------

@transaction.atomic
def reverse_entry(*, entry_id: int, by, reason: str) -> WalletEntry:
    if not reason.strip():
        raise WalletError("ثبت دلیل برای سند معکوس الزامی است.")

    entry = (
        WalletEntry.objects
        .select_for_update()
        .get(pk=entry_id)
    )

    if entry.kind == WalletEntry.KIND.REVERSAL:
        raise WalletError("سند معکوس را نمی‌توان دوباره معکوس کرد.")

    if hasattr(entry, "reversed_by"):
        raise WalletError("این سند قبلاً معکوس شده است.")

    return WalletEntry.objects.create(
        user=entry.user,
        direction=(
            WalletEntry.DIRECTION.DEBIT
            if entry.direction == WalletEntry.DIRECTION.CREDIT
            else WalletEntry.DIRECTION.CREDIT
        ),
        amount=entry.amount,
        kind=WalletEntry.KIND.REVERSAL,
        title=f"برگشت: {entry.title}"[:255],
        description=reason.strip(),
        created_by=by,
        reverses=entry,
        payment=entry.payment,
        order=entry.order,
        ai_order=entry.ai_order,
    )
