from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    CourseManagementViewSet,
    CourseCatalogView,
    CourseCatalogCategoryView,
    CourseDetailView,
    HomeworkSubmissionView,
    SessionSourceCodeView,
    MyCourseHomeworkView,
    GiftVideoListView,
    GiftVideoDetailView,
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
    path(
        "sessions/<int:session_id>/homework/",
        HomeworkSubmissionView.as_view(),
        name="session-homework",
    ),
    path(
        "sessions/<int:session_id>/source-code/",
        SessionSourceCodeView.as_view(),
        name="session-source-code",
    ),
    path(
        "catalog/<slug:slug>/",
        CourseDetailView.as_view(),
        name="course-detail",
    ),
    path(
        "homework/mine/",
        MyCourseHomeworkView.as_view(),
        name="my-course-homework",
    ),
    path(
        "gift-videos/",
        GiftVideoListView.as_view(),
        name="gift-video-list",
    ),

    path(
        "gift-videos/<slug:slug>/",
        GiftVideoDetailView.as_view(),
        name="gift-video-detail",
    ),
]