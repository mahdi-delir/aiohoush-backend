from django.urls import path

from .views import LoginOTPRequestView, LoginOTPVerifyView


urlpatterns = [
    path(
        "auth/request-otp/",
        LoginOTPRequestView.as_view(),
        name="login-request-otp",
    ),
    path(
        "auth/login/verify-otp/",
        LoginOTPVerifyView.as_view(),
        name="login-verify-otp",
    ),
]