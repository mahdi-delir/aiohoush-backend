from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    AIProductCheckoutView,
    AIProductPaymentReturnView,
    OrderManagementViewSet,
)


router = DefaultRouter()

router.register(
    "manage/orders",
    OrderManagementViewSet,
    basename="manage-order",
)

urlpatterns = [
    path(
        "ai-products/checkout/",
        AIProductCheckoutView.as_view(),
        name="ai-product-checkout",
    ),
    path(
        "ai-products/payment-return/",
        AIProductPaymentReturnView.as_view(),
        name="ai-product-payment-return",
    ),
]

urlpatterns += router.urls
