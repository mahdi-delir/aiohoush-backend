# user/api/views/auth.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from notification.models import OTPSMSToken
from notification.tasks import send_otp_sms

from .throttles import (
    OTPIPRateThrottle,
    OTPMobileRateThrottle,
    OTPVerifyIPRateThrottle,
    OTPVerifyMobileRateThrottle    
)

from notification.services.otp import InvalidOTPError

from .serializers import LoginOTPRequestSerializer, LoginOTPVerifySerializer
from .models import User
from .services.auth import InactiveUserError, login_with_otp

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

        return Response(
            {
                'success':True,
                'called_by': 'webapp',
                "message": _("کد یکبار مصرف برای شما ارسال خواهد شد.")
            },
            status=status.HTTP_202_ACCEPTED,
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
            return Response(
                {
                    "detail": _(
                        "کد یکبار مصرف معتبر نیست."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tokens = login_with_otp(
                user=user,
                raw_code=code,
            )

        except (InvalidOTPError, InactiveUserError):
            return Response(
                {
                    "detail": _(
                        "کد یکبار مصرف معتبر نیست."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            tokens,
            status=status.HTTP_200_OK,
        )