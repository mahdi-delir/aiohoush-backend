from .digits import normalize_number_to_en
from .validators import mobile_validator


def normalize_mobile_to_09(mobile):
    mobile = normalize_number_to_en(mobile)
    mobile_validator(mobile)

    if mobile.startswith("+98"):
        return "0" + mobile[3:]

    if mobile.startswith("98"):
        return "0" + mobile[2:]

    if mobile.startswith("9"):
        return "0" + mobile

    return mobile