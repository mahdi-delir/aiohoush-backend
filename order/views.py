from django.db import transaction

from rest_framework import (
    mixins,
    status,
)
from rest_framework.decorators import action
from rest_framework.viewsets import (
    GenericViewSet,
)


from course.models import Course

from .models import Order, AIProductOrder

from .permissions import (
    OrderManagementPermission,
)
from .serializers import (
    OrderSerializer,
)
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError

from aiohoush.core.responses import APIResponse

from .services import videopol


logger = logging.getLogger(__name__)


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
        order = get_object_or_404(
            self.get_queryset()
            .select_for_update(
                 of=("self",)
            ),
            pk=pk,
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
        order = get_object_or_404(
            self.get_queryset()
            .select_for_update(
                 of=("self",)
            ),
            pk=pk,
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

AI_PRODUCTS = {
    "chatgpt-monthly": {
        "title": "اکانت ChatGPT ماهانه",
        "amount_rial": 55_000_000,
    },
    "claude-monthly": {
        "title": "اکانت Claude ماهانه",
        "amount_rial": 90_000_000,
    },
    "pixverse-monthly": {
        "title": "اکانت PixVerse ماهانه",
        "amount_rial": 140_000_000,
    },
    "higgsfield-monthly": {
        "title": "اکانت Higgsfield ماهانه",
        "amount_rial": 60_000_000,
    },
}


class AIProductCheckoutView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    # عمداً atomic نیست: درخواست HTTP به ویدوپل نباید تراکنش
    # دیتابیس را باز نگه دارد.
    def post(self, request):
        product_code = request.data.get("product_code")

        product = AI_PRODUCTS.get(product_code)

        if product is None:
            return APIResponse(
                success=False,
                called_by="webapp",
                message="محصول انتخاب‌شده معتبر نیست.",
                status=status.HTTP_200_OK,
            )

        order = AIProductOrder.objects.create(
            user=request.user,
            product_code=product_code,
            amount_rial=product["amount_rial"],
        )

        try:
            payment = videopol.create_payment(
                order_id=str(order.id),
                product_code=product_code,
                amount_rial=product["amount_rial"],
                mobile=request.user.mobile,
                callback_url=settings.AI_PAYMENT_CALLBACK_URL,
            )
        except videopol.VideopolError:
            logger.exception(
                "Videopol payment creation failed for AI order %s",
                order.id,
            )

            order.status = AIProductOrder.STATUS.FAILED
            order.save(update_fields=["status", "updated_at"])

            return APIResponse(
                success=False,
                called_by="webapp",
                message="ایجاد پرداخت ناموفق بود. لطفاً دوباره تلاش کنید.",
                status=status.HTTP_502_BAD_GATEWAY,
            )

        order.videopol_payment_id = payment.payment_id
        order.payment_url = payment.gateway_url
        order.save(
            update_fields=[
                "videopol_payment_id",
                "payment_url",
                "updated_at",
            ]
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="درخواست پرداخت ایجاد شد.",
            data={
                "order_id": str(order.id),
                "payment_url": order.payment_url,
            },
            status=status.HTTP_200_OK,
        )


class AIProductPaymentReturnView(APIView):
    """بازگشت مرورگر کاربر از ویدوپل بعد از درگاه.

    پارامترهای URL (payment_id و status) قابل جعل‌اند؛ فقط payment_id
    برای پیدا کردن سفارش استفاده می‌شود و وضعیت واقعی از API ویدوپل
    استعلام می‌شود. در پایان کاربر به صفحهٔ نتیجه در فرانت هدایت می‌شود.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        payment_id = str(
            request.query_params.get("payment_id", "")
        ).strip()

        if not payment_id.isdigit():
            return self._redirect("failed")

        order = (
            AIProductOrder.objects
            .filter(videopol_payment_id=payment_id)
            .only("id", "status")
            .first()
        )

        if order is None:
            logger.warning(
                "Payment return for unknown videopol payment %s",
                payment_id,
            )
            return self._redirect("failed")

        if order.status == AIProductOrder.STATUS.PAID:
            return self._redirect("paid", order.id)

        try:
            remote = videopol.get_payment_status(payment_id)
        except videopol.VideopolError:
            logger.exception(
                "Videopol status lookup failed for AI order %s",
                order.id,
            )
            return self._redirect("pending", order.id)

        result = apply_videopol_payment_status(
            order_id=order.id,
            remote=remote,
        )

        return self._redirect(result, order.id)

    @staticmethod
    def _redirect(result, order_id=None):
        query = {"payment": result}

        if order_id is not None:
            query["order"] = str(order_id)

        return HttpResponseRedirect(
            f"{settings.AI_PAYMENT_RESULT_URL}?{urlencode(query)}"
        )


@transaction.atomic
def apply_videopol_payment_status(
    *,
    order_id,
    remote,
) -> str:
    """وضعیت استعلام‌شده از ویدوپل را روی سفارش اعمال می‌کند.

    خروجی: "paid" یا "failed" یا "pending".
    """
    order = (
        AIProductOrder.objects
        .select_for_update()
        .get(pk=order_id)
    )

    if order.status == AIProductOrder.STATUS.PAID:
        return "paid"

    # پرداخت باید دقیقاً متعلق به همین سفارش و همین مبلغ باشد.
    if (
        remote.order_id != str(order.id)
        or remote.payment_id != order.videopol_payment_id
        or remote.product_code != order.product_code
        or remote.amount_rial != order.amount_rial
    ):
        logger.error(
            "Videopol payment %s does not match AI order %s",
            remote.payment_id,
            order.id,
        )
        return "failed"

    if remote.status == "success":
        order.status = AIProductOrder.STATUS.PAID
        order.reference_id = remote.reference_id
        order.paid_at = timezone.now()
        order.save(
            update_fields=[
                "status",
                "reference_id",
                "paid_at",
                "updated_at",
            ]
        )
        return "paid"

    if remote.status in {"failed", "canceled"}:
        if order.status == AIProductOrder.STATUS.PENDING:
            order.status = (
                AIProductOrder.STATUS.CANCELLED
                if remote.status == "canceled"
                else AIProductOrder.STATUS.FAILED
            )
            order.save(update_fields=["status", "updated_at"])
        return "failed"

    # created / pending: هنوز نتیجهٔ قطعی نداریم.
    return "pending"
