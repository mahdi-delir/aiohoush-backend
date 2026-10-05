from django.contrib import admin, messages

from order.services.orders import (
    OrderActionError,
    approve_order,
    reject_order,
)
from order.models import (
    AIProductOrder,
    Order,
    OrderComment,
    RequestedProduct,
)


def _order_is_locked(order) -> bool:
    """اقلام سفارش بعد از بررسی تغییر نمی‌کنند؛ سند کیف پول بر اساس آن‌هاست."""
    return order is not None and order.status != Order.STATUS.PENDING


class RequestedProductInline(admin.TabularInline):
    model = RequestedProduct
    extra = 0

    def has_add_permission(self, request, obj=None):
        return not _order_is_locked(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not _order_is_locked(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not _order_is_locked(obj) and super().has_delete_permission(request, obj)

    autocomplete_fields = (
        "course",
    )

    fields = (
        "course",
        "price",
        "discount",
    )


class OrderCommentInline(admin.TabularInline):
    model = OrderComment
    extra = 0

    autocomplete_fields = (
        "user",
    )

    fields = (
        "user",
        "comment",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "status",
        "seller",
        "created_by",
        "checked_by",
        "is_deleted",
        "created_at",
    )

    list_filter = (
        "status",
        "is_deleted",
        "created_at",
    )

    search_fields = (
        "student__mobile",
        "seller__mobile",
        "created_by__mobile",
        "checked_by__mobile",
    )

    list_select_related = (
        "student",
        "seller",
        "created_by",
        "checked_by",
    )

    autocomplete_fields = (
        "student",
        "seller",
        "created_by",
        "checked_by",
    )

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    inlines = (
        RequestedProductInline,
        OrderCommentInline,
    )

    # وضعیت فقط با اکشن تأیید/رد عوض می‌شود تا سند خرید در کیف پول
    # دانشجو ثبت شود.
    readonly_fields = (
        "status",
        "checked_by",
    )

    actions = (
        "approve_selected",
        "reject_selected",
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def _change_status(self, request, queryset, permission, service, done_message):
        if not request.user.has_perm(permission):
            self.message_user(
                request,
                "اجازهٔ این کار را ندارید.",
                level=messages.ERROR,
            )
            return

        done = 0
        for order in queryset:
            try:
                service(order_id=order.pk, by=request.user)
                done += 1
            except OrderActionError as exc:
                self.message_user(
                    request,
                    f"سفارش {order.pk}: {exc}",
                    level=messages.WARNING,
                )

        if done:
            self.message_user(request, done_message.format(count=done))

    @admin.action(description="تأیید سفارش‌های انتخاب‌شده (کسر از کیف پول)")
    def approve_selected(self, request, queryset):
        self._change_status(
            request,
            queryset,
            "order.approve_order",
            approve_order,
            "{count} سفارش تأیید شد.",
        )

    @admin.action(description="رد سفارش‌های انتخاب‌شده")
    def reject_selected(self, request, queryset):
        self._change_status(
            request,
            queryset,
            "order.reject_order",
            reject_order,
            "{count} سفارش رد شد.",
        )


@admin.register(RequestedProduct)
class RequestedProductAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is not None and _order_is_locked(obj.order):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and _order_is_locked(obj.order):
            return False
        return super().has_delete_permission(request, obj)

    list_display = (
        "id",
        "order",
        "course",
        "price",
        "discount",
    )

    list_select_related = (
        "order",
        "course",
    )

    search_fields = (
        "course__title",
        "order__student__mobile",
    )

    autocomplete_fields = (
        "order",
        "course",
    )


@admin.register(OrderComment)
class OrderCommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "user",
        "created_at",
    )

    list_select_related = (
        "order",
        "user",
    )

    search_fields = (
        "user__mobile",
        "comment",
    )

    autocomplete_fields = (
        "order",
        "user",
    )


@admin.register(AIProductOrder)
class AIProductOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "product_code",
        "amount_rial",
        "status",
        "reference_id",
        "paid_at",
        "created_at",
        'videopol_payment_id'
    )

    list_filter = (
        "status",
        "product_code",
        "created_at",
    )

    search_fields = (
        "id",
        "user__mobile",
        "videopol_payment_id",
        "reference_id",
    )

    list_select_related = (
        "user",
    )

    date_hierarchy = "created_at"

    # وضعیت پرداخت فقط از طریق استعلام ویدوپل تغییر می‌کند.
    readonly_fields = (
        "id",
        "user",
        "product_code",
        "amount_rial",
        "status",
        "videopol_payment_id",
        "payment_url",
        "reference_id",
        "paid_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
