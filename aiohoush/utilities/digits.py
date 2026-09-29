import re


DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

WHITESPACE_REGEX = re.compile(r"[\s\u200c\u200b]+")


def normalize_number_to_en(value):
    if not isinstance(value, str):
        value = str(value)

    value = value.translate(DIGIT_TRANSLATION)
    return WHITESPACE_REGEX.sub("", value)