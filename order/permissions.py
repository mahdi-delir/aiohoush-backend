from rest_framework.permissions import (
    BasePermission,
)

from order.models import Order


class OrderManagementPermission(
    BasePermission
):
    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        action = view.action

        if action in {
            "list",
            "retrieve",
        }:
            return (
                user.has_perm(
                    "order.view_all_orders"
                )
                or
                user.has_perm(
                    "order.view_order"
                )
            )

        if action == "create":
            return user.has_perm(
                "order.add_order"
            )

        if action in {
            "update",
            "partial_update",
        }:
            return user.has_perm(
                "order.change_order"
            )

        if action == "destroy":
            return user.has_perm(
                "order.delete_order"
            )

        if action == "approve":
            return user.has_perm(
                "order.approve_order"
            )

        if action == "reject":
            return user.has_perm(
                "order.reject_order"
            )

        return False

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user
        action = view.action

        if action == "retrieve":
            if user.has_perm(
                "order.view_all_orders"
            ):
                return True

            return (
                user.has_perm(
                    "order.view_order"
                )
                and
                obj.seller_id == user.id
            )

        if action in {
            "update",
            "partial_update",
            "destroy",
        }:
            if user.has_perm(
                "order.change_any_order"
            ):
                return True

            return (
                obj.seller_id == user.id
                and
                obj.status
                in {
                    Order.STATUS.PENDING,
                    Order.STATUS.DRAFT,
                }
            )

        if action == "approve":
            return user.has_perm(
                "order.approve_order"
            )

        if action == "reject":
            return user.has_perm(
                "order.reject_order"
            )

        return False