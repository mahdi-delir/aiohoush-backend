from django.urls import path

from .views import (
    LoginOTPRequestView,
    LoginOTPVerifyView,
    RefreshTokenView,
    LogoutView,
    LogoutAllView,
    ActiveSessionsView,
    RevokeSessionView,
    MeView
    )


urlpatterns = [
    path(
        "login/request-otp/",
        LoginOTPRequestView.as_view(),
        name="login-request-otp",
    ),
    path(
        "login/verify-otp/",
        LoginOTPVerifyView.as_view(),
        name="login-verify-otp",
    ),
    path(
    "token/refresh/",
        RefreshTokenView.as_view(),
        name="token-refresh",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path(
        "logout-all/",
        LogoutAllView.as_view(),
        name="logout-all",
    ),
    path(
        "sessions/",
        ActiveSessionsView.as_view(),
        name="active-sessions",
    ),
    path(
        "sessions/<uuid:session_id>/revoke/",
        RevokeSessionView.as_view(),
        name="revoke-session",
    ),
    path(
        "me/",
        MeView.as_view(),
        name="auth-me",
    ),
]