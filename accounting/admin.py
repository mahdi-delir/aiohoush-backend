from django.contrib import admin

from accounting.models import (
    BankAccount,
    Payment,
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
        "order",
        "amount",
        "gateway",
        "tracking_code",
        "paid_at",
        "is_deleted",
    )

    list_filter = (
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
    )

    autocomplete_fields = (
        "user",
        "bank",
        "created_by",
        "order",
    )

    date_hierarchy = "paid_at"

    ordering = (
        "-paid_at",
    )