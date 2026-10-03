from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    CourseManagementViewSet,
    CourseCatalogView,
    CourseCatalogCategoryView

)


router = DefaultRouter()

router.register(
    "manage/courses",
    CourseManagementViewSet,
    basename="manage-course",
)

urlpatterns = router.urls

urlpatterns += [
    path(
        "catalog/",
        CourseCatalogView.as_view(),
        name="course-catalog",
    ),
    path(
        "catalog/categories/",
        CourseCatalogCategoryView.as_view(),
        name="course-catalog-categories",
    ),
]