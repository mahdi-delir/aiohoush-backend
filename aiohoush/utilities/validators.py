import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .digits import normalize_number_to_en


MOBILE_REGEX = re.compile(r"(?:\+98|98|0)?9[0-9]{9}")
TEN_DIGITS_REGEX = re.compile(r"[0-9]{10}")


def mobile_validator(mobile):
    mobile = normalize_number_to_en(mobile)

    if not MOBILE_REGEX.fullmatch(mobile):
        raise ValidationError(
            _("شماره موبایل معتبر نیست."),
            code="invalid_mobile",
        )


def national_id_validator(national_id):
    national_id = normalize_number_to_en(national_id)

    if not TEN_DIGITS_REGEX.fullmatch(national_id):
        raise ValidationError(
            _("کد ملی باید ۱۰ رقم باشد."),
            code="invalid_national_id",
        )

    if len(set(national_id)) == 1:
        raise ValidationError(
            _("کد ملی معتبر نیست."),
            code="invalid_national_id",
        )

    check_digit = int(national_id[-1])

    weighted_sum = sum(
        int(national_id[index]) * (10 - index)
        for index in range(9)
    )

    remainder = weighted_sum % 11
    expected_digit = remainder if remainder < 2 else 11 - remainder

    if check_digit != expected_digit:
        raise ValidationError(
            _("کد ملی معتبر نیست."),
            code="invalid_national_id",
        )


def postal_code_validator(postal_code):
    postal_code = normalize_number_to_en(postal_code)

    if not TEN_DIGITS_REGEX.fullmatch(postal_code):
        raise ValidationError(
            _("کد پستی باید ۱۰ رقم باشد."),
            code="invalid_postal_code",
        )

    if len(set(postal_code)) == 1:
        raise ValidationError(
            _("کد پستی معتبر نیست."),
            code="invalid_postal_code",
        )