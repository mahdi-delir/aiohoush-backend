import re
from .validators import mobile_validator

FA_TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
AR_TO_EN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

def normalize_number_to_en(number):
    if not isinstance(number, str):
        number = str(number)
    number = re.sub(r'[\s\u200c\u200b]', '', number)
    number = number.translate(FA_TO_EN).translate(AR_TO_EN)
    return number

def normalize_mobile_to_09(mobile):
    mobile = normalize_number_to_en(mobile)
    mobile_validator(mobile)

    if mobile.startswith('+98'):
        mobile = '0' + mobile[3:]
    elif mobile.startswith('98'):
        mobile = '0' + mobile[2:]
    elif mobile.startswith('9'):
        mobile = '0' + mobile

    return mobile