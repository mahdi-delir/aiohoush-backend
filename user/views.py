from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse

from notification.models import OTPSMSToken
from notification.tasks import send_otp_sms, send_welcome_sms

from .throttles import (
    OTPIPRateThrottle,
    OTPMobileRateThrottle,
    OTPVerifyIPRateThrottle,
    OTPVerifyMobileRateThrottle    
)

from notification.services.otp import InvalidOTPError

from .serializers import (
    LoginOTPRequestSerializer,
    LoginOTPVerifySerializer,
    SessionTokenRefreshSerializer,
    LogoutSerializer,
    AuthSessionSerializer,
    DeviceTicketSerializer,
    DeviceRevokeSerializer,
    MeResponseSerializer
    )
from .models import User
from .services.auth import (
    device_limit_sessions,
    free_device_and_login,
    login_with_otp,
    logout_session,
    logout_all_sessions,
    revoke_other_session
    )
from .selectors.me import get_user_data
from .services.devices import active_sessions


def _tokens_response(tokens):
    return APIResponse(
        success=True,
        called_by='webapp',
        message=_('توکن با موفقیت صادر شد.'),
        data=tokens,
        status=status.HTTP_200_OK,
    )


def _device_limit_response(user, ticket, sessions):
    return APIResponse(
        success=False,
        called_by='webapp',
        message=_('به حداکثر تعداد دستگاه‌های مجاز رسیده‌اید. برای ورود، از یکی از دستگاه‌ها خارج شوید.'),
        data={
            'code': 'device_limit',
            'ticket': ticket,
            'max_devices': user.max_devices,
            'sessions': AuthSessionSerializer(sessions, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


def _login_result_response(result):
    if result.tokens is not None:
        return _tokens_response(result.tokens)
    user, sessions = device_limit_sessions(result.ticket)
    return _device_limit_response(user, result.ticket, sessions)

class LoginOTPRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    throttle_classes = [
        OTPIPRateThrottle,
        OTPMobileRateThrottle,
    ]


    @transaction.atomic
    def post(self, request):
        serializer = LoginOTPRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]

        user, created = User.objects.get_or_create(
            mobile=mobile,
        )

        if created:
            user.set_unusable_password()
            user.full_clean()
            user.save(
                update_fields=["password"]
            )
            student_group = Group.objects.get(
                name="دانشجویان",
            )

            user.groups.add(student_group)
            send_welcome_sms.delay_on_commit(
                user_id=user.pk,
            )

        send_otp_sms.delay_on_commit(
            user_id=user.pk,
            reason=OTPSMSToken.OTPREASON.LOGIN,
        )

        return APIResponse(
            success=True,
            called_by='webapp',
            message='درخواست ارسال پیامک انجام شد.',
            status=status.HTTP_202_ACCEPTED,
            data={"expires_in": settings.OTP_EXPIRATION_SECONDS}
        )

class LoginOTPVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    throttle_classes = [
        OTPVerifyIPRateThrottle,
        OTPVerifyMobileRateThrottle,
    ]

    def post(self, request):
        serializer = LoginOTPVerifySerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        mobile = serializer.validated_data["mobile"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(
                mobile=mobile
            )
        except User.DoesNotExist:
            raise InvalidOTPError

        result = login_with_otp(
            user=user,
            raw_code=code,
            request = request
        )

        return _login_result_response(result)


class LoginDeviceRevokeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyIPRateThrottle]

    def post(self, request):
        serializer = DeviceRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = free_device_and_login(
            ticket=serializer.validated_data["ticket"],
            session_id=serializer.validated_data["session_id"],
            request=request,
        )
        return _login_result_response(result)


class LoginDeviceRevokeAllView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyIPRateThrottle]

    def post(self, request):
        serializer = DeviceTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = free_device_and_login(
            ticket=serializer.validated_data["ticket"],
            revoke_all=True,
            request=request,
        )
        return _login_result_response(result)

class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SessionTokenRefreshSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        return APIResponse(
            success=True,
            message=_("توکن با موفقیت بروزرسانی شد."),
            called_by='webapp',
            data=serializer.validated_data,
            status=status.HTTP_200_OK,
        )

class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LogoutSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        logout_session(
            raw_refresh=serializer.validated_data["refresh"],
        )

        return APIResponse(
            success=True,
            message=_("خروج با موفقیت انجام شد."),
            called_by='webapp',
            status=status.HTTP_200_OK,
        )

class LogoutAllView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        logout_all_sessions(
            user=request.user,
        )

        return APIResponse(
            success=True,
            message=_(
                "خروج از تمام دستگاه‌ها با موفقیت انجام شد."
            ),
            called_by='webapp',
            status=status.HTTP_200_OK,
        )

class ActiveSessionsView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        current_sid = request.auth.get("sid")

        sessions = active_sessions(request.user)

        serializer = AuthSessionSerializer(
            sessions,
            many=True,
            context={
                "current_sid": current_sid,
            },
        )

        return APIResponse(
            success=True,
            message=_("نشست‌های فعال دریافت شدند."),
            called_by='webapp',
            data=serializer.data,
        )

class RevokeSessionView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        session_id: UUID,
    ):
        current_sid = request.auth.get("sid")

        revoke_other_session(
            user=request.user,
            current_session_id=current_sid,
            target_session_id=session_id,
        )

        return APIResponse(
            success=True,
            called_by='webapp',
            message=_(
                "نشست موردنظر با موفقیت خاتمه یافت."
            ),
            data={}
        )

class MeView(APIView):
    permission_classes = (
        IsAuthenticated,
    )

    def get(self, request):
        user = request.user

        data = {
            "user": {
                "id": user.pk,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "mobile": user.mobile,
                # از روی خود فیلدها، تا کاربرانی که نامشان از ادمین
                # پر شده هم «تکمیل‌شده» حساب شوند.
                "is_profile_completed": user.has_complete_profile,
            },

            "groups": list(
                user.groups
                .order_by("name")
                .values_list(
                    "name",
                    flat=True,
                )
            ),

            "permissions": sorted(
                user.get_all_permissions()
            ),

            "user_data": get_user_data(
                user=user,
            ),
        }

        serializer = MeResponseSerializer(
            instance=data,
        )

        return APIResponse(
            success=True,
            message=(
                "دریافت اطلاعات از سرور "
                "با موفقیت انجام شد."
            ),
            called_by='webapp',
            data=serializer.data,
        )

class ProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from .serializers import ProfileSerializer
        return APIResponse(
            success=True, message="پروفایل دریافت شد.", called_by="webapp",
            data=ProfileSerializer(request.user).data,
        )

    def patch(self, request):
        from .serializers import ProfileSerializer
        serializer = ProfileSerializer(
            request.user, data=request.data, partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return APIResponse(
            success=True, message="پروفایل با موفقیت بروزرسانی شد.", called_by="webapp",
            data=ProfileSerializer(serializer.save(), context={"request": request}).data,
        )


class ProfilePicturesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from .serializers import ProfilePictureSerializer
        pictures = request.user.user_pictures_qs()
        return APIResponse(
            success=True, message="تصاویر پروفایل دریافت شد.", called_by="webapp",
            data=ProfilePictureSerializer(
                pictures, many=True, context={"request": request}
            ).data,
        )

    def post(self, request):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from aiohoush.utilities.uploads import validate_profile_picture

        from .models import UserProfilePicture
        from .serializers import ProfilePictureSerializer

        picture = request.FILES.get("picture")
        if not picture:
            return APIResponse(
                success=False, message="فایل تصویر ارسال نشده است.",
                called_by="webapp", status=status.HTTP_200_OK,
            )

        # نوع تصویر از روی محتوا تشخیص داده می‌شود، نه Content-Type
        # یا پسوندی که کاربر فرستاده.
        try:
            extension = validate_profile_picture(picture)
        except DjangoValidationError as exc:
            return APIResponse(
                success=False, message=exc.messages[0],
                called_by="webapp", status=status.HTTP_200_OK,
            )

        picture.name = f"avatar{extension}"

        obj = UserProfilePicture.objects.create(user=request.user, picture=picture)
        return APIResponse(
            success=True, message="تصویر با موفقیت آپلود شد.", called_by="webapp",
            data=ProfilePictureSerializer(obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProfilePictureDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, picture_id):
        from .models import UserProfilePicture
        picture = UserProfilePicture.objects.filter(
            id=picture_id, user=request.user, is_deleted=False,
        ).first()
        if picture is None:
            return APIResponse(
                success=False, message="تصویر پیدا نشد.", called_by="webapp",
                status=status.HTTP_200_OK,
            )
        picture.is_deleted = True
        picture.save(update_fields=("is_deleted",))
        return APIResponse(
            success=True, message="تصویر حذف شد.", called_by="webapp", data={},
        )


def _mentor_failure(message):
    return APIResponse(
        success=False,
        called_by="webapp",
        message=message,
        status=status.HTTP_200_OK,
    )


def _review_row(review):
    from .services.mentor import full_name

    return {
        "id": review.pk,
        "authorName": full_name(review.student),
        "rating": review.rating,
        "text": review.text,
        "createdAt": review.created_at.isoformat(),
    }


class MyMentorView(APIView):
    """منتور فعلی دانشجو، نظرهای همهٔ دانشجویان او و وضعیت درخواست منتور."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from .models import MentorRequest, MentorReview
        from .services.mentor import avatar_url, full_name, get_active_mentor

        student = request.user
        mentor = get_active_mentor(student)

        open_request = (
            MentorRequest.objects
            .filter(student=student, status=MentorRequest.STATUS.OPEN)
            .first()
        )

        if mentor is None:
            return APIResponse(
                success=True,
                called_by="webapp",
                message="منتوری برای شما تعیین نشده است.",
                data={
                    "mentor": None,
                    "reviews": [],
                    "myReview": None,
                    "mentorRequest": (
                        {"createdAt": open_request.created_at.isoformat()}
                        if open_request
                        else None
                    ),
                },
            )

        reviews = list(
            MentorReview.objects
            .filter(mentor=mentor, is_published=True)
            .select_related("student")
            .order_by("-created_at")
        )
        my_review = next(
            (review for review in reviews if review.student_id == student.pk),
            None,
        ) or (
            MentorReview.objects
            .filter(mentor=mentor, student=student)
            .select_related("student")
            .first()
        )

        return APIResponse(
            success=True,
            called_by="webapp",
            message="اطلاعات منتور دریافت شد.",
            data={
                "mentor": {
                    "id": mentor.pk,
                    "name": full_name(mentor),
                    # فیلدهای عنوان و تخصص هنوز در مدل نیستند.
                    "headline": "",
                    "specialties": [],
                    "bio": mentor.bio or "",
                    "avatarUrl": avatar_url(mentor, request),
                    "mobile": mentor.mobile,
                    "telegramId": mentor.telegram_id or None,
                },
                "reviews": [_review_row(review) for review in reviews],
                "myReview": _review_row(my_review) if my_review else None,
                "mentorRequest": None,
            },
        )


class MyMentorReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from .services.mentor import MentorActionError, submit_review

        try:
            rating = int(request.data.get("rating"))
        except (TypeError, ValueError):
            return _mentor_failure("امتیاز را از ۱ تا ۵ انتخاب کنید.")

        if not 1 <= rating <= 5:
            return _mentor_failure("امتیاز را از ۱ تا ۵ انتخاب کنید.")

        text = request.data.get("text") or ""
        if not isinstance(text, str):
            return _mentor_failure("متن نظر معتبر نیست.")
        if len(text.strip()) > 1000:
            return _mentor_failure("متن نظر نباید بیشتر از ۱۰۰۰ حرف باشد.")

        try:
            review = submit_review(
                student=request.user,
                rating=rating,
                text=text,
            )
        except MentorActionError as exc:
            return _mentor_failure(str(exc))

        return APIResponse(
            success=True,
            called_by="webapp",
            message="نظر شما ثبت شد.",
            data=_review_row(review),
            status=status.HTTP_201_CREATED,
        )


class MentorRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from .services.mentor import MentorActionError, request_mentor

        try:
            mentor_request = request_mentor(student=request.user)
        except MentorActionError as exc:
            return _mentor_failure(str(exc))

        return APIResponse(
            success=True,
            called_by="webapp",
            message="درخواست شما ثبت شد. به‌زودی منتور شما تعیین می‌شود.",
            data={"createdAt": mentor_request.created_at.isoformat()},
        )
