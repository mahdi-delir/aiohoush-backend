from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    OrderManagementViewSet,
)


router = DefaultRouter()

router.register(
    "manage/orders",
    OrderManagementViewSet,
    basename="manage-order",
)

urlpatterns = router.urls