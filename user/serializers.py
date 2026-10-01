from django.conf import settings

from rest_framework import serializers

from .models import User

mobile_model_field = User._meta.get_field("mobile")


class LoginOTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=mobile_model_field.max_length,
        validators=list(mobile_model_field.validators),
        trim_whitespace=False,
    )

class LoginOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=mobile_model_field.max_length,
        validators=list(mobile_model_field.validators),
        trim_whitespace=False,
    )

    code = serializers.RegexField(
        regex=rf"^\d{{{settings.OTP_LENGTH}}}$",
        min_length=settings.OTP_LENGTH,
        max_length=settings.OTP_LENGTH,
        trim_whitespace=False,
    )