# user/api/views/auth.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse

from notification.models import OTPSMSToken
from notification.tasks import send_otp_sms

from .throttles import (
    OTPIPRateThrottle,
    OTPMobileRateThrottle,
    OTPVerifyIPRateThrottle,
    OTPVerifyMobileRateThrottle    
)

from notification.services.otp import InvalidOTPError

from .serializers import LoginOTPRequestSerializer, LoginOTPVerifySerializer, SessionTokenRefreshSerializer, LogoutSerializer
from .models import User
from .services.auth import login_with_otp, logout_session

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
            status=status.HTTP_200_OK,
        )