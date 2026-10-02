from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    CourseManagementViewSet,
)


router = DefaultRouter()

router.register(
    "manage/courses",
    CourseManagementViewSet,
    basename="manage-course",
)

urlpatterns = router.urls