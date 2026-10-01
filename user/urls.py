from django.urls import path

from .views import LoginOTPRequestView, LoginOTPVerifyView, RefreshTokenView


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
    path(
    "auth/token/refresh/",
        RefreshTokenView.as_view(),
        name="token-refresh",
    ),
]