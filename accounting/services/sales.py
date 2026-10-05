"""ثبت فروش به نام فروشنده (برای رتبه‌بندی منتورها).

فروشنده = فروشندهٔ سفارشی که پرداخت به آن وصل است؛ اگر سفارش یا
فروشنده‌ای نباشد، منتور فعال دانشجو در لحظهٔ ثبت پرداخت.
"""

from accounting.models import Payment, SalesCredit
from user.models import StudentMentorAssignment


def resolve_seller(payment: Payment):
    if payment.order_id and payment.order.seller_id:
        return payment.order.seller

    assignment = (
        StudentMentorAssignment.objects
        .filter(student_id=payment.user_id, is_active=True)
        .select_related("mentor")
        .first()
    )
    return assignment.mentor if assignment else None


def credit_sale(payment: Payment) -> SalesCredit | None:
    """برای پرداخت تأییدشده یک بار صدا زده می‌شود (داخل همان تراکنش)."""
    seller = resolve_seller(payment)

    if seller is None:
        return None

    if SalesCredit.objects.filter(
        payment=payment,
        kind=SalesCredit.KIND.SALE,
    ).exists():
        return None

    return SalesCredit.objects.create(
        seller=seller,
        amount=int(payment.amount),
        kind=SalesCredit.KIND.SALE,
        payment=payment,
    )
