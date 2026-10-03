from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    OrderManagementViewSet,
    AIProductCheckoutView
)

from django.urls import path



router = DefaultRouter()

router.register(
    "manage/orders",
    OrderManagementViewSet,
    basename="manage-order",
)

urlpatterns = router.urls


urlpatterns = [
    path(
        "ai-products/checkout/",
        AIProductCheckoutView.as_view(),
        name="ai-product-checkout",
    ),
]