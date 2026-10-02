from django.contrib import admin

from order.models import (
    Order,
    OrderComment,
    RequestedProduct,
)


class RequestedProductInline(admin.TabularInline):
    model = RequestedProduct
    extra = 0

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


@admin.register(RequestedProduct)
class RequestedProductAdmin(admin.ModelAdmin):
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