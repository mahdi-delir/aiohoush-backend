from django.utils import timezone
from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
    Sum,
)
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from aiohoush.core.responses import APIResponse
from course.models import Course, CourseCategory, CourseSessionHomeworkSubmission
from .permissions import CourseManagementPermission
from .serializers import CourseSerializer, CourseCatalogCategorySerializer, CourseCatalogSerializer, HomeworkSubmissionSerializer
from order.models import Order, RequestedProduct

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

class CourseCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        access = (
            RequestedProduct.objects
            .filter(
                course_id=OuterRef("pk"),
                order__student=user,
                order__status=(
                    Order.STATUS.APPROVED
                ),
                order__is_deleted=False,
            )
        )

        queryset = Course.objects.annotate(
            has_access=Exists(access), 
            all_sessions=Count("seasons__sessions", distinct=True),
            season_count=Count("seasons",distinct=True),
            completed_sessions=Count("seasons__sessions", filter=Q(
                seasons__sessions__user_progresses__user=user, seasons__sessions__user_progresses__completed_at__isnull=False), distinct=True),
                total_duration=Sum("seasons__sessions__duration"),
            ).filter(Q(has_access=True) | Q(is_published=True, can_sale=True,)
            ).prefetch_related("categories"
            ).order_by("order", "id"
            )
        

        
        category = (
            request.query_params.get(
                "category"
            )
        )

        if category:
            queryset = queryset.filter(
                categories__slug=category,
            )

        serializer = (
            CourseCatalogSerializer(
                queryset,
                many=True,
                context={
                    "request": request,
                },
            )
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "دوره‌ها با موفقیت "
                "دریافت شدند."
            ),
            data={
                "courses":
                    serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class CourseCatalogCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            CourseCategory.objects
            .order_by(
                "order",
                "id",
            )
        )

        serializer = (
            CourseCatalogCategorySerializer(
                queryset,
                many=True,
            )
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "دسته‌بندی‌ها با موفقیت "
                "دریافت شدند."
            ),
            data={
                "categories":
                    serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class HomeworkSubmissionView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    parser_classes = [
        JSONParser,
        FormParser,
        MultiPartParser,
    ]

    def get_session(
        self,
        request,
        session_id,
    ):
        session = get_object_or_404(
            CourseSession.objects
            .select_related(
                "season__course",
            ),
            pk=session_id,
        )

        if not session.has_homework:
            raise ValidationError(
                "این جلسه تمرین ندارد."
            )

        has_access = (
            RequestedProduct.objects
            .filter(
                course=session.season.course,
                order__student=request.user,
                order__status=(
                    Order.STATUS.APPROVED
                ),
                order__is_deleted=False,
            )
            .exists()
        )

        if not has_access:
            raise PermissionDenied(
                "به این دوره دسترسی ندارید."
            )

        return session

    def get(
        self,
        request,
        session_id,
    ):
        session = self.get_session(
            request,
            session_id,
        )

        submission = (
            CourseSessionHomeworkSubmission
            .objects
            .filter(
                session=session,
                student=request.user,
            )
            .first()
        )

        if submission is None:
            return APIResponse(
                success=True,
                called_by="webapp",
                message=(
                    "هنوز تمرینی ارسال "
                    "نشده است."
                ),
                data=None,
                status=status.HTTP_200_OK,
            )

        serializer = (
            HomeworkSubmissionSerializer(
                submission,
                context={
                    "request": request,
                },
            )
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "تمرین با موفقیت "
                "دریافت شد."
            ),
            data=serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(
        self,
        request,
        session_id,
    ):
        session = self.get_session(
            request,
            session_id,
        )

        submission = (
            CourseSessionHomeworkSubmission
            .objects
            .select_for_update()
            .filter(
                session=session,
                student=request.user,
            )
            .first()
        )

        if (
            submission
            and submission.status
            == CourseSessionHomeworkSubmission
            .STATUS.REVIEWED
        ):
            raise ValidationError(
                "این تمرین بررسی شده و "
                "دیگر قابل ویرایش نیست."
            )

        serializer = (
            HomeworkSubmissionSerializer(
                instance=submission,
                data=request.data,
                context={
                    "request": request,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        created = submission is None

        submission = serializer.save(
            session=session,
            student=request.user,
            status=(
                CourseSessionHomeworkSubmission
                .STATUS.SUBMITTED
            ),
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message=(
                "تمرین با موفقیت "
                "ارسال شد."
            ),
            data=(
                HomeworkSubmissionSerializer(
                    submission,
                    context={
                        "request": request,
                    },
                ).data
            ),
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )
    