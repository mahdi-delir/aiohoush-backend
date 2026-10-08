from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    CourseManagementViewSet,
    CourseCatalogView,
    RecommendedCourseView,
    CourseCatalogCategoryView,
    CourseDetailView,
    HomeworkSubmissionView,
    SessionSourceCodeView,
    SessionWatchStartView,
    WatchEventsView,
    MyCourseHomeworkView,
    HomeworkAttachmentView,
    GiftVideoListView,
    GiftVideoDetailView,
    GiftWatchEventsView,
    GiftWatchStartView,
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
        "recommended/",
        RecommendedCourseView.as_view(),
        name="course-recommended",
    ),
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
        "sessions/<int:session_id>/watch/",
        SessionWatchStartView.as_view(),
        name="session-watch-start",
    ),
    path(
        "watches/<uuid:watch_id>/events/",
        WatchEventsView.as_view(),
        name="watch-events",
    ),
    path(
        "catalog/<slug:slug>/",
        CourseDetailView.as_view(),
        name="course-detail",
    ),
    path(
        "homework/<int:submission_id>/attachment/",
        HomeworkAttachmentView.as_view(),
        name="homework-attachment",
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
        "gift-videos/<int:gift_id>/watch/",
        GiftWatchStartView.as_view(),
        name="gift-watch-start",
    ),
    path(
        "gift-watches/<uuid:watch_id>/events/",
        GiftWatchEventsView.as_view(),
        name="gift-watch-events",
    ),
    path(
        "gift-videos/<slug:slug>/",
        GiftVideoDetailView.as_view(),
        name="gift-video-detail",
    ),
]