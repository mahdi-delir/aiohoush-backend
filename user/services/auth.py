from django.db import transaction

from rest_framework_simplejwt.tokens import RefreshToken

from notification.models import OTPSMSToken
from notification.services.otp import (
    InvalidOTPError,
    verify_otp,
)
from user.models import User

class InactiveUserError(Exception):
    pass

@transaction.atomic
def login_with_otp(
    *,
    user:User,
    raw_code: str,
) -> dict[str, str]:
    user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )
    if not user.is_active:
        raise InactiveUserError
    verify_otp(
        user=user,
        raw_code=raw_code,
        reason=OTPSMSToken.OTPREASON.LOGIN,
    )
    if not user.is_mobile_verified:
        user.is_mobile_verified = True
        user.full_clean()
        user.save(
            update_fields=[
                "is_mobile_verified",
                "date_updated",
            ]
        )
    if not user.is_mobile_verified:
        raise InvalidOTPError
    refresh = RefreshToken.for_user(user)
    return {
        'success': True,
        'message': 'دریافت توکن با موفقیت انجام شد.',
        'called_by': 'webapp',
        'data' : {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    }
