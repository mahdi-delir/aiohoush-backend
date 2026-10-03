from django.db import transaction

from rest_framework import (
    mixins,
    status,
)
from rest_framework.decorators import action
from rest_framework.viewsets import (
    GenericViewSet,
)

from aiohoush.core.responses import (
    APIResponse,
)

from course.models import Course

from order.models import Order

from .permissions import (
    OrderManagementPermission,
)
from .serializers import (
    OrderSerializer,
)


class OrderManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = OrderSerializer

    permission_classes = [
        OrderManagementPermission,
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Order.objects
            .filter(
                is_deleted=False,
            )
            .select_related(
                "student",
                "seller",
                "created_by",
                "checked_by",
            )
            .prefetch_related(
                "requested_products__course",
            )
        )

        if user.has_perm(
            "order.view_all_orders"
        ):
            return queryset

        return queryset.filter(
            seller=user,
        )

    def perform_create(
        self,
        serializer,
    ):
        user = self.request.user

        if user.has_perm(
            "order.change_any_order"
        ):
            serializer.save(
                created_by=user,
            )
            return

        serializer.save(
            seller=user,
            created_by=user,
        )

    def perform_update(
        self,
        serializer,
    ):
        user = self.request.user

        if user.has_perm(
            "order.change_any_order"
        ):
            serializer.save()
            return

        serializer.save(
            seller=user,
        )

    def perform_destroy(
        self,
        instance,
    ):
        # Soft delete
        instance.is_deleted = True

        instance.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ]
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    @transaction.atomic
    def approve(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update(
                 of=("self",)
            )
            .get(pk=pk)
        )

        self.check_object_permissions(
            request,
            order,
        )
        if order.status != Order.STATUS.PENDING:
            return APIResponse(
                success=False,
                called_by="webapp",
                message=(
                    "فقط سفارش در انتظار بررسی "
                    "قابل تأیید است."
                ),
                status=status.HTTP_200_OK,
            )

        order.status = (
            Order.STATUS.APPROVED
        )
        order.checked_by = request.user

        order.save(
            update_fields=[
                "status",
                "checked_by",
                "updated_at",
            ]
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "سفارش با موفقیت "
                "تأیید شد."
            ),
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    @transaction.atomic
    def reject(
        self,
        request,
        pk=None,
    ):
        order = (
            self.get_queryset()
            .select_for_update(
                 of=("self",)
            )
            .get(pk=pk)
        )

        self.check_object_permissions(
            request,
            order,
        )

        if order.status != Order.STATUS.PENDING:
            return APIResponse(
                success=False,
                called_by="webapp",
                message=(
                    "فقط سفارش در انتظار بررسی "
                    "قابل رد است."
                ),
                status=status.HTTP_200_OK,
            )

        order.status = (
            Order.STATUS.REJECTED
        )
        order.checked_by = request.user

        order.save(
            update_fields=[
                "status",
                "checked_by",
                "updated_at",
            ]
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "سفارش رد شد."
            ),
            status=status.HTTP_200_OK,
        )
    @action(
    detail=False,
    methods=["get"],
    url_path="options",
    )
    def sale_options(
        self,
        request,
    ):
        courses = (
            Course.objects
            .filter(
                can_sale=True,
            )
            .order_by(
                "order",
                "id",
            )
            .values(
                "id",
                "title",
                "price",
            )
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "اطلاعات ثبت سفارش "
                "با موفقیت دریافت شد."
            ),
            data={
                "courses": list(courses),
            },
            status=status.HTTP_200_OK,
        )
    def list(
        self,
        request,
        *args,
        **kwargs,
    ):
        queryset = self.filter_queryset(
            self.get_queryset()
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "سفارش‌ها با موفقیت "
                "دریافت شدند."
            ),
            data=serializer.data,
            status=status.HTTP_200_OK,
        )


    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        self.perform_create(
            serializer,
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "سفارش با موفقیت "
                "ثبت شد."
            ),
            data=serializer.data,
            status=status.HTTP_201_CREATED,
        )
    def retrieve(
            self,
            request,
            *args,
            **kwargs,
        ):
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "اطلاعات سفارش با موفقیت "
                "دریافت شد."
            ),
            data=serializer.data,
            status=status.HTTP_200_OK,
        )