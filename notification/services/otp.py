import secrets
from datetime import timedelta

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone

from notification.models import OTPSMSToken
from user.models import User as UserModel


User = get_user_model()

class InvalidOTPError(Exception):
    pass

def generate_numeric_otp(length: int = 6) -> str:
    if length <= 0:
        raise ValueError(_('طول کد یکبار مصرف باید بیشتر از 0 باشد.'))
    return "".join(
        str(secrets.randbelow(10)) for x in range(length)
    )

@transaction.atomic
def create_otp(
    *,
    user: UserModel,
    reason: str,
    length: int,
) -> tuple[OTPSMSToken, str]:

    # Serialize concurrent OTP creation for this user.
    User.objects.select_for_update().get(pk=user.pk)

    now = timezone.now()

    OTPSMSToken.objects.filter(
        user=user,
        consumed_at__isnull=True,
        revoked_at__isnull=True,
    ).update(
        revoked_at=now,
    )

    raw_code = generate_numeric_otp(length)

    otp = OTPSMSToken(
        user=user,
        reason=reason,
        code_hash=make_password(raw_code),
        expires_at=now + timedelta(
            seconds=settings.OTP_EXPIRATION_SECONDS
        ),
    )
    otp.full_clean()
    otp.save()

    return otp, raw_code

@transaction.atomic
def verify_otp(
    *,
    user: UserModel,
    raw_code: str,
    reason: str
) -> OTPSMSToken:
    now = timezone.now()
    otp = OTPSMSToken.objects.select_for_update().filter(
        user=user,
        consumed_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=now,
        reason = reason
    ).order_by('-created_at').first()
    if otp is None:
        raise ValueError(_('کد یکبارمصرف معتبر نیست.'))
    if not check_password(raw_code, otp.code_hash):
        raise ValueError(_('کد یکبارمصرف معتبر نیست.'))
    otp.consumed_at = now
    otp.save(update_fields=['consumed_at'])
    return otp