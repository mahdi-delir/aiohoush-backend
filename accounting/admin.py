from django.contrib import admin, messages

from accounting.models import (
    BankAccount,
    Payment,
    WalletEntry,
    WalletTopUp,
)
from accounting.services.wallet import (
    WalletError,
    confirm_payment,
    reject_payment,
)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "bank",
        "card_number",
        "account_number",
    )

    list_filter = (
        "bank",
    )

    search_fields = (
        "owner__mobile",
        "card_number",
        "sheba",
        "account_number",
    )

    list_select_related = (
        "owner",
    )

    autocomplete_fields = (
        "owner",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "gateway",
        "status",
        "tracking_code",
        "paid_at",
        "reviewed_by",
    )

    list_filter = (
        "status",
        "gateway",
        "is_deleted",
        "paid_at",
    )

    search_fields = (
        "user__mobile",
        "tracking_code",
        "order__student__mobile",
    )

    list_select_related = (
        "user",
        "bank",
        "created_by",
        "order",
        "reviewed_by",
    )

    autocomplete_fields = (
        "user",
        "bank",
        "order",
    )

    date_hierarchy = "paid_at"

    ordering = (
        "-paid_at",
    )

    fields = (
        "user",
        "amount",
        "paid_at",
        "gateway",
        "tracking_code",
        "user_card_digits",
        "bank",
        "order",
        "status",
        "created_by",
        "reviewed_by",
        "reviewed_at",
        "ai_order",
        "top_up",
    )

    # وضعیت فقط با اکشن‌های تأیید/رد عوض می‌شود تا سند کیف پول ثبت شود.
    base_readonly_fields = (
        "status",
        "created_by",
        "reviewed_by",
        "reviewed_at",
        "ai_order",
        "top_up",
    )

    actions = (
        "confirm_selected",
        "reject_selected",
    )

    def get_readonly_fields(self, request, obj=None):
        # بعد از بررسی، هیچ فیلدی قابل تغییر نیست.
        if obj is not None and obj.status != Payment.STATUS.PENDING:
            return self.fields
        return self.base_readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.status = Payment.STATUS.PENDING
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False

    def _review(self, request, queryset, service, done_message):
        if not request.user.has_perm("accounting.confirm_payment"):
            self.message_user(
                request,
                "اجازهٔ تأیید یا رد پرداخت را ندارید.",
                level=messages.ERROR,
            )
            return

        done = 0
        for payment in queryset:
            try:
                service(payment_id=payment.pk, by=request.user)
                done += 1
            except WalletError as exc:
                self.message_user(
                    request,
                    f"پرداخت {payment.pk}: {exc}",
                    level=messages.WARNING,
                )

        if done:
            self.message_user(request, done_message.format(count=done))

    @admin.action(description="تأیید پرداخت‌های انتخاب‌شده (شارژ کیف پول)")
    def confirm_selected(self, request, queryset):
        self._review(
            request,
            queryset,
            confirm_payment,
            "{count} پرداخت تأیید و به کیف پول اضافه شد.",
        )

    @admin.action(description="رد پرداخت‌های انتخاب‌شده")
    def reject_selected(self, request, queryset):
        self._review(
            request,
            queryset,
            reject_payment,
            "{count} پرداخت رد شد.",
        )


@admin.register(WalletEntry)
class WalletEntryAdmin(admin.ModelAdmin):
    """فقط مشاهده؛ اسناد از طریق سرویس کیف پول ثبت می‌شوند."""

    list_display = (
        "id",
        "user",
        "direction",
        "amount",
        "kind",
        "title",
        "created_by",
        "created_at",
    )

    list_filter = (
        "kind",
        "direction",
        "created_at",
    )

    search_fields = (
        "user__mobile",
        "title",
    )

    list_select_related = (
        "user",
        "created_by",
    )

    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WalletTopUp)
class WalletTopUpAdmin(admin.ModelAdmin):
    """فقط مشاهده؛ وضعیت فقط با استعلام از ویدوپل تغییر می‌کند."""

    list_display = (
        "id",
        "user",
        "amount_rial",
        "status",
        "reference_id",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
