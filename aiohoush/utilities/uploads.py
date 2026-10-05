"""اعتبارسنجی فایل‌های آپلودی کاربران.

نوع فایل از روی محتوا/پسوند بررسی می‌شود، نه Content-Type که کاربر
می‌فرستد. فایل‌هایی که مرورگر می‌تواند به‌عنوان صفحه اجرا کند
(HTML/SVG/XML) هرگز پذیرفته نمی‌شوند، چون از دامنهٔ API سرو می‌شوند
و می‌توانند در همان origin (مثلاً پنل ادمین) اسکریپت اجرا کنند.
"""

from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MB = 1024 * 1024

HOMEWORK_MAX_BYTES = 5 * MB

# HTML/SVG/XML عمداً در این لیست نیستند؛ تمرین وب را zip کنید.
HOMEWORK_ALLOWED_EXTENSIONS = frozenset({
    ".zip", ".rar", ".7z",
    ".pdf", ".txt", ".md",
    ".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx",
    ".css", ".json", ".java", ".c", ".cpp", ".cs", ".php", ".sql",
    ".png", ".jpg", ".jpeg", ".webp",
})

PROFILE_PICTURE_MAX_BYTES = 2 * MB

# فرمت‌های PIL → پسوند ذخیره‌شده
PROFILE_PICTURE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

PROFILE_PICTURE_MAX_PIXELS = 4096 * 4096


def _size_text(max_bytes: int) -> str:
    return f"{max_bytes // MB} مگابایت"


def validate_homework_attachment(file) -> None:
    if file.size > HOMEWORK_MAX_BYTES:
        raise ValidationError(
            f"حجم فایل نباید بیشتر از {_size_text(HOMEWORK_MAX_BYTES)} باشد."
        )

    extension = Path(file.name or "").suffix.lower()

    if extension not in HOMEWORK_ALLOWED_EXTENSIONS:
        raise ValidationError(
            "این نوع فایل پذیرفته نمی‌شود. "
            "برای چند فایل یا پروژهٔ وب، آن را zip کنید."
        )


def validate_profile_picture(file) -> str:
    """تصویر را واقعاً باز می‌کند و پسوند امن متناظر را برمی‌گرداند."""
    if file.size > PROFILE_PICTURE_MAX_BYTES:
        raise ValidationError(
            f"حجم تصویر نباید بیشتر از {_size_text(PROFILE_PICTURE_MAX_BYTES)} باشد."
        )

    try:
        file.seek(0)
        with Image.open(file) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("فایل ارسال‌شده تصویر معتبر نیست.")
    finally:
        file.seek(0)

    if image_format not in PROFILE_PICTURE_FORMATS:
        raise ValidationError("فقط تصاویر JPG، PNG و WEBP پذیرفته می‌شوند.")

    if width * height > PROFILE_PICTURE_MAX_PIXELS:
        raise ValidationError("ابعاد تصویر بیش از حد بزرگ است.")

    return PROFILE_PICTURE_FORMATS[image_format]


TICKET_ATTACHMENT_MAX_BYTES = HOMEWORK_MAX_BYTES
TICKET_ATTACHMENT_ALLOWED_EXTENSIONS = HOMEWORK_ALLOWED_EXTENSIONS

VOICE_MAX_BYTES = 10 * MB

# خروجی MediaRecorder: Chrome/Firefox → webm/ogg، Safari → mp4 (m4a)
VOICE_ALLOWED_EXTENSIONS = frozenset({
    ".webm", ".ogg", ".oga", ".m4a", ".mp4", ".mp3", ".wav", ".aac",
})


def validate_ticket_attachment(file) -> None:
    if file.size > TICKET_ATTACHMENT_MAX_BYTES:
        raise ValidationError(
            f"حجم فایل نباید بیشتر از {_size_text(TICKET_ATTACHMENT_MAX_BYTES)} باشد."
        )

    extension = Path(file.name or "").suffix.lower()

    if extension not in TICKET_ATTACHMENT_ALLOWED_EXTENSIONS:
        raise ValidationError(
            "این نوع فایل پذیرفته نمی‌شود. برای چند فایل، آن‌ها را zip کنید."
        )


def validate_voice_message(file) -> None:
    if file.size > VOICE_MAX_BYTES:
        raise ValidationError(
            f"حجم پیام صوتی نباید بیشتر از {_size_text(VOICE_MAX_BYTES)} باشد."
        )

    extension = Path(file.name or "").suffix.lower()

    if extension not in VOICE_ALLOWED_EXTENSIONS:
        raise ValidationError("فرمت پیام صوتی پشتیبانی نمی‌شود.")
