from django.utils import timezone

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.viewsets import (
    GenericViewSet,
)

from aiohoush.core.responses import APIResponse

from course.models import Course

from .permissions import (
    CourseManagementPermission,
)
from .serializers import (
    CourseSerializer,
)


class CourseManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = CourseSerializer

    permission_classes = [
        CourseManagementPermission,
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Course.objects
            .select_related("teacher")
            .prefetch_related(
                "categories",
                "requirements",
            )
        )

        if user.has_perm(
            "course.view_all_courses"
        ):
            return queryset

        return queryset.filter(
            teacher=user,
        )

    def perform_create(
        self,
        serializer,
    ):
        user = self.request.user

        # مدیریت می‌تواند استاد دوره
        # را از request مشخص کند.
        if user.has_perm(
            "course.change_any_course"
        ):
            serializer.save()
            return

        # استاد همیشه فقط می‌تواند
        # دوره را برای خودش ایجاد کند.
        serializer.save(
            teacher=user,
        )

    def perform_update(
        self,
        serializer,
    ):
        user = self.request.user

        # مدیریت اجازه تغییر teacher
        # را هم دارد.
        if user.has_perm(
            "course.change_any_course"
        ):
            serializer.save()
            return

        # استاد نمی‌تواند مالک دوره
        # را تغییر دهد.
        serializer.save(
            teacher=user,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="publish",
    )
    def publish(
        self,
        request,
        pk=None,
    ):
        course = self.get_object()

        course.is_published = True

        if course.published_at is None:
            course.published_at = (
                timezone.now()
            )

        course.save(
            update_fields=[
                "is_published",
                "published_at",
            ]
        )

        return APIResponse(
            success=True,
            called_by='webapp',
            message='دوره با موفقیت منتشر شد.',
            status=status.HTTP_200_OK
        )