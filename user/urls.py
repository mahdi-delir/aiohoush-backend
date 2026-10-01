from django.urls import path

from .views import (
    LoginOTPRequestView,
    LoginOTPVerifyView,
    RefreshTokenView,
    LogoutView,
    LogoutAllView,
    ActiveSessionsView,
    RevokeSessionView,
    )


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
    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path(
        "auth/logout-all/",
        LogoutAllView.as_view(),
        name="logout-all",
    ),
    path(
        "auth/sessions/",
        ActiveSessionsView.as_view(),
        name="active-sessions",
    ),
    path(
        "auth/sessions/<uuid:session_id>/revoke/",
        RevokeSessionView.as_view(),
        name="revoke-session",
    ),
]