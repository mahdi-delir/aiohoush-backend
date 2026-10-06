import logging
from pathlib import Path

from django.http import FileResponse, Http404
from django.utils import timezone
from django.db.models import (
    Count,
    DurationField,
    Exists,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
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
from .access import (
    annotate_has_purchased,
    can_access_course,
    can_access_session,
    has_purchased_course,
)
from .models import Course, CourseCategory, CourseSeason, CourseSessionHomeworkSubmission, CourseSession, CourseSessionProgress, CourseSessionWatch, GiftVideo, GiftVideoProgress
from .services import watch as watch_service
from .services import gift_watch as gift_watch_service
from .permissions import CourseManagementPermission
from .serializers import (
    CourseSerializer,
    CourseCatalogCategorySerializer,
    CourseCatalogSerializer,
    CourseDetailSerializer,
    HomeworkSubmissionSerializer,
    GiftVideoSerializer,
    WatchBatchInputSerializer,
)
from order.models import Order, RequestedProduct


logger = logging.getLogger(__name__)

def course_total_duration():
    """مجموع مدت جلسات دوره به صورت subquery.

    Sum روی همان کوئری‌ای که با user_progresses JOIN شده، مدت هر جلسه
    را به تعداد ردیف‌های پیشرفت ضرب می‌کرد؛ subquery از آن JOIN جداست.
    """
    totals = (
        CourseSession.objects
        .filter(season__course=OuterRef("pk"))
        .order_by()
        .values("season__course")
        .annotate(total=Sum("duration"))
        .values("total")[:1]
    )

    return Subquery(totals, output_field=DurationField())


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
                total_duration=course_total_duration(),
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

def failure_response(message, *, detail=None):
    """خطای قابل‌پیش‌بینی: HTTP 200 با success=false (قرارداد پروژه)."""
    return APIResponse(
        success=False,
        called_by="webapp",
        message=message,
        detail=detail,
        status=status.HTTP_200_OK,
    )


def first_error_message(errors, default="اطلاعات ارسالی معتبر نیست."):
    """اولین پیام خطای serializer برای نمایش به کاربر."""
    if isinstance(errors, dict):
        for value in errors.values():
            message = first_error_message(value, default=None)
            if message:
                return message
    elif isinstance(errors, (list, tuple)):
        for value in errors:
            message = first_error_message(value, default=None)
            if message:
                return message
    elif errors:
        return str(errors)
    return default


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
        """(session, None) یا (None, پاسخ خطا)"""
        session = (
            CourseSession.objects
            .select_related(
                "season__course",
            )
            .filter(pk=session_id)
            .first()
        )

        if session is None:
            return None, failure_response("جلسه پیدا نشد.")

        if not session.has_homework:
            return None, failure_response("این جلسه تمرین ندارد.")

        if not has_purchased_course(
            request.user,
            session.season.course,
        ):
            return None, failure_response("به این دوره دسترسی ندارید.")

        return session, None

    def get(
        self,
        request,
        session_id,
    ):
        session, error = self.get_session(
            request,
            session_id,
        )

        if error:
            return error

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
        session, error = self.get_session(
            request,
            session_id,
        )

        if error:
            return error

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
            return failure_response(
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

        if not serializer.is_valid():
            return failure_response(
                first_error_message(serializer.errors),
                detail=serializer.errors,
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


class CourseDetailView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, slug):
        user = request.user

        queryset = (
            annotate_has_purchased(
                Course.objects.all(),
                user,
            )
            .annotate(
                all_sessions=Count(
                    "seasons__sessions",
                    distinct=True,
                ),
                season_count=Count(
                    "seasons",
                    distinct=True,
                ),
                completed_sessions=Count(
                    "seasons__sessions__user_progresses",
                    filter=Q(
                        seasons__sessions__user_progresses__user=user,
                        seasons__sessions__user_progresses__completed_at__isnull=False,
                    ),
                    distinct=True,
                ),
                total_duration=course_total_duration(),
            )
            .prefetch_related(
                "categories",
                Prefetch(
                    "seasons",
                    queryset=CourseSeason.objects.order_by(
                        "order",
                        "id",
                    ),
                ),
                Prefetch(
                    "seasons__sessions",
                    queryset=CourseSession.objects.order_by(
                        "order",
                        "id",
                    ),
                ),
            )
        )

        course = queryset.filter(slug=slug).first()

        if course is None:
            return failure_response("دوره پیدا نشد.")

        course_access = can_access_course(
            user,
            course,
            has_purchased=course.has_purchased,
        )

        if not course_access and not (
            course.is_published and course.can_sale
        ):
            return failure_response(
                "به این دوره دسترسی ندارید."
            )

        # has_access در خروجی یعنی «امکان مشاهدهٔ کامل دوره»
        course.has_access = course_access
        course.watched_percent = (
            round(course.completed_sessions * 100 / course.all_sessions)
            if course.all_sessions
            else 0
        )

        progress_by_session = {
            progress.session_id: progress
            for progress in CourseSessionProgress.objects.filter(
                user=user,
                session__season__course=course,
            )
        }

        serializer = CourseDetailSerializer(
            course,
            context={
                "request": request,
                "can_access_course": course_access,
                "progress_by_session": progress_by_session,
            },
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="اطلاعات دوره با موفقیت دریافت شد.",
            data=serializer.data,
            status=status.HTTP_200_OK,
        )


class SessionSourceCodeView(APIView):
    """دانلود سورس کد جلسه فقط برای کاربر دارای دسترسی."""

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, session_id):
        session = (
            CourseSession.objects
            .select_related("season__course")
            .filter(pk=session_id)
            .first()
        )

        if session is None:
            return failure_response("جلسه پیدا نشد.")

        if not can_access_session(request.user, session):
            return failure_response("به این جلسه دسترسی ندارید.")

        if not session.source_code:
            return failure_response("این جلسه سورس کد ندارد.")

        try:
            file = session.source_code.open("rb")
        except FileNotFoundError:
            # فایل در دیتابیس ثبت شده ولی روی دیسک نیست: مشکل واقعی سرور
            logger.error(
                "Source code file missing for session %s: %s",
                session.pk,
                session.source_code.name,
            )
            raise Http404("فایل سورس کد پیدا نشد.")

        return FileResponse(
            file,
            as_attachment=True,
            filename=Path(session.source_code.name).name,
        )


class MyCourseHomeworkView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        course_id = request.query_params.get("course")

        if not course_id or not str(course_id).isdigit():
            return failure_response("شناسه دوره الزامی است.")

        submissions = (
            CourseSessionHomeworkSubmission.objects
            .filter(
                student=request.user,
                session__season__course_id=course_id,
            )
            .select_related(
                "session",
                "session__season",
            )
            .order_by("-submitted_at")
        )

        serializer = HomeworkSubmissionSerializer(
            submissions,
            many=True,
            context={
                "request": request,
            },
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تمرین‌های دوره با موفقیت دریافت شدند.",
            data=serializer.data,
            status=status.HTTP_200_OK,
        )

class GiftVideoListView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        videos = (
            GiftVideo.objects
            .filter(
                is_active=True,
                is_public=True,
            )
            .order_by(
                "order",
                "id",
            )
        )

        serializer = GiftVideoSerializer(
            videos,
            many=True,
            context={
                "request": request,
            },
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="ویدئوهای هدیه با موفقیت دریافت شدند.",
            data={
                "videos": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class GiftVideoDetailView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, slug):
        video = get_object_or_404(
            GiftVideo.objects.filter(
                is_active=True,
                is_public=True,
            ),
            slug=slug,
        )

        serializer = GiftVideoSerializer(
            video,
            context={
                "request": request,
            },
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="ویدئوی هدیه با موفقیت دریافت شد.",
            data=serializer.data,
            status=status.HTTP_200_OK,
        )


class SessionWatchStartView(APIView):
    """شروع یک نوبت تماشا؛ موقعیت ادامهٔ پخش را برمی‌گرداند."""

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, session_id):
        session = (
            CourseSession.objects
            .select_related("season__course")
            .filter(pk=session_id)
            .first()
        )

        if session is None:
            return failure_response("جلسه پیدا نشد.")

        if not can_access_session(request.user, session):
            return failure_response("به این جلسه دسترسی ندارید.")

        watch, progress = watch_service.start_watch(
            user=request.user,
            session=session,
            auth_session_id=request.auth.get("sid") if request.auth else None,
        )

        duration_ms = watch_service.session_duration_ms(session)

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تماشا ثبت شد.",
            data={
                "watch_id": str(watch.pk),
                "resume_position_ms": progress.last_position_ms,
                "completed": progress.completed_at is not None,
                "watched_percent": watch_service.progress_percent(
                    progress,
                    duration_ms,
                ),
            },
            status=status.HTTP_200_OK,
        )


class WatchEventsView(APIView):
    """دریافت batch رویدادها و بازه‌های دیده‌شدهٔ یک نوبت تماشا."""

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, watch_id):
        watch = (
            CourseSessionWatch.objects
            .select_related("progress__session__season__course")
            .filter(
                pk=watch_id,
                progress__user=request.user,
            )
            .first()
        )

        if watch is None:
            return failure_response("نوبت تماشا پیدا نشد.")

        # اگر دسترسی در این فاصله گرفته شده باشد (مثلاً سفارش لغو شده)
        if not can_access_session(request.user, watch.progress.session):
            return failure_response("به این جلسه دسترسی ندارید.")

        serializer = WatchBatchInputSerializer(data=request.data)

        if not serializer.is_valid():
            return failure_response(
                first_error_message(serializer.errors),
                detail=serializer.errors,
            )

        data = serializer.validated_data

        state = watch_service.record_watch_batch(
            watch=watch,
            events=data["events"],
            ranges=data["ranges"],
            position_ms=data["position_ms"],
            client_duration_ms=data.get("duration_ms"),
            end_reason=data.get("end_reason"),
        )

        if state is None:
            return failure_response("این نوبت تماشا بسته شده است.")

        return APIResponse(
            success=True,
            called_by="webapp",
            message="پیشرفت ثبت شد.",
            data={
                "unique_watched_ms": state.unique_watched_ms,
                "watched_percent": state.watched_percent,
                "last_position_ms": state.last_position_ms,
                "completed": state.completed,
            },
            status=status.HTTP_200_OK,
        )


class GiftWatchStartView(APIView):
    """شروع تماشای ویدئوی هدیه؛ موقعیت ادامهٔ پخش را برمی‌گرداند."""

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, gift_id):
        gift = gift_watch_service.visible_gifts().filter(pk=gift_id).first()

        if gift is None:
            return failure_response("ویدئوی هدیه پیدا نشد.")

        progress = gift_watch_service.start_gift_watch(user=request.user, gift=gift)

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تماشا ثبت شد.",
            data={
                "watch_id": str(progress.watch_token),
                "resume_position_ms": progress.last_position_ms,
                "completed": progress.completed_at is not None,
            },
            status=status.HTTP_200_OK,
        )


class GiftWatchEventsView(APIView):
    """batch بازه‌های دیده‌شدهٔ ویدئوی هدیه (همان قالب جلسات دوره)."""

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, watch_id):
        progress = (
            GiftVideoProgress.objects
            .filter(watch_token=watch_id, user=request.user)
            .only("pk")
            .first()
        )

        if progress is None:
            return failure_response("نوبت تماشا پیدا نشد.")

        serializer = WatchBatchInputSerializer(data=request.data)

        if not serializer.is_valid():
            return failure_response(
                first_error_message(serializer.errors),
                detail=serializer.errors,
            )

        data = serializer.validated_data

        state = gift_watch_service.record_gift_batch(
            progress_id=progress.pk,
            ranges=data["ranges"],
            position_ms=data["position_ms"],
            client_duration_ms=data.get("duration_ms"),
            ended=any(event["event_type"] == "ended" for event in data["events"]),
            end_reason=data.get("end_reason"),
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="پیشرفت ثبت شد.",
            data={
                "watched_percent": state.watched_percent,
                "completed": state.completed,
            },
            status=status.HTTP_200_OK,
        )
