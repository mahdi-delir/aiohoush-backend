import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "یک جفت کلید VAPID برای Web Push می‌سازد (فقط یک بار لازم است)."

    def handle(self, *args, **options):
        key = ec.generate_private_key(ec.SECP256R1())
        private = _b64url(key.private_numbers().private_value.to_bytes(32, "big"))
        public = _b64url(
            key.public_key().public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )

        self.stdout.write("این دو خط را در .env بک‌اند بگذارید:\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={public}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private}")
        self.stdout.write(self.style.WARNING(
            "\nکلید خصوصی را جایی منتشر نکنید. اگر بعداً عوضش کنید، همهٔ کاربران باید "
            "دوباره نوتیفیکیشن را فعال کنند."
        ))
