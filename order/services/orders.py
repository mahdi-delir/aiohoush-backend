"""تأیید و رد سفارش دوره.

تأیید سفارش همزمان سند خرید را در کیف پول دانشجو ثبت می‌کند. هم API
و هم پنل ادمین از همین تابع استفاده می‌کنند تا سفارشی بدون سند تأیید
نشود.
"""

from django.db import transaction

from accounting.services.wallet import debit_course_order
from order.models import Order


class OrderActionError(Exception):
    """خطای قابل‌نمایش به کاربر."""


@transaction.atomic
def approve_order(*, order_id: int, by) -> Order:
    order = (
        Order.objects
        .select_for_update(of=("self",))
        .select_related("student")
        .get(pk=order_id, is_deleted=False)
    )

    if order.status != Order.STATUS.PENDING:
        raise OrderActionError("فقط سفارش در انتظار بررسی قابل تأیید است.")

    order.status = Order.STATUS.APPROVED
    order.checked_by = by
    order.save(update_fields=["status", "checked_by", "updated_at"])

    # موجودی منفی مجاز است: فعلاً فقط حسابداری و مدیر اصلی
    # (مجوز approve_order) سفارش را تأیید می‌کنند.
    debit_course_order(order=order, by=by)

    return order


@transaction.atomic
def reject_order(*, order_id: int, by) -> Order:
    order = (
        Order.objects
        .select_for_update(of=("self",))
        .get(pk=order_id, is_deleted=False)
    )

    if order.status != Order.STATUS.PENDING:
        raise OrderActionError("فقط سفارش در انتظار بررسی قابل رد است.")

    order.status = Order.STATUS.REJECTED
    order.checked_by = by
    order.save(update_fields=["status", "checked_by", "updated_at"])

    return order
