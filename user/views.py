from uuid import UUID

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
    MeResponseSerializer
    )
from .models import User, AuthSession
from .services.auth import (
    login_with_otp,
    logout_session,
    logout_all_sessions,
    revoke_other_session
    )
from .selectors.me import get_user_data

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
            data={}
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

        tokens = login_with_otp(
            user=user,
            raw_code=code,
            request = request
        )


        return APIResponse(
            success=True,
            called_by='webapp',
            message=_('توکن با موفقیت صادر شد.'),
            data=tokens,
            status=status.HTTP_200_OK,
        )

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

        sessions = (
            AuthSession.objects
            .filter(
                user=request.user,
                revoked_at__isnull=True,
            )
            .order_by("-created_at")
        )

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
