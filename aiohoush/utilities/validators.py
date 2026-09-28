import re

from .normalizers import normalize_number_to_en

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MOBILE_REGEX = re.compile(r'^(\+98|98|0)?9\d{9}$')
POST_CODE_REGEX = re.compile(r'^\d{10}$')

def mobile_validator(mobile):
    """
    تابع صحت سنجی موبایل
    +989121111111 صحیح
    989121111111 صحیح
    9121111111 صحیح
    09121111111 صحیح
    :param mobile:
    :return:
    """
    mobile = normalize_number_to_en(mobile)

    if not MOBILE_REGEX.fullmatch(mobile):
        raise ValidationError(_('شماره موبایل معتبر نیست'), code='invalid_mobile')

def national_id_validator(national_id):
    
    national_id = normalize_number_to_en(national_id)
    
    if not national_id.isdigit or len(national_id) != 10:
        raise ValidationError(_('کد ملی باید 10 رقم باشد'), code='invalid_national_id')
    
    if national_id == national_id[0]*10:
        raise ValidationError(_('کدملی صحیح نیست'), code='invalid_national_id')

    check_digit = int(national_id[-1])
    total = sum(int(national_id[i]) * (10 - i) for i in range(len(national_id)))
    reminder = total % 11
    is_correct = check_digit == reminder if reminder < 2 else check_digit == (11 - reminder)

    if is_correct == False:
        raise ValidationError(_('کدملی صحیح نیست'), code='invalid_national_id')

def postal_code_validator(postal_code):
    postal_code = normalize_number_to_en(postal_code)
    if not POST_CODE_REGEX.fullmatch(postal_code):
        raise ValidationError(_('کد پستی باید 10 رقم باشد'), code='invalid_postal_code')
    if postal_code == postal_code[0] * 10:
        raise ValidationError(_('کد پستی معتبر نیست'), code='invalid_postal_code')

