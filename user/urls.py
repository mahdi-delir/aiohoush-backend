from django.urls import path

from .views import (
    LoginOTPRequestView,
    LoginOTPVerifyView,
    RefreshTokenView,
    LogoutView,
    LogoutAllView,
    ActiveSessionsView,
    RevokeSessionView,
    MeView,
    ProfileView,
    ProfilePicturesView,
    ProfilePictureDeleteView,
    MyMentorView,
    MyMentorReviewView,
    MentorRequestView,
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
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/pictures/", ProfilePicturesView.as_view(), name="profile-pictures"),
    path("profile/pictures/<int:picture_id>/", ProfilePictureDeleteView.as_view(), name="profile-picture-delete"),
    path("my-mentor/", MyMentorView.as_view(), name="my-mentor"),
    path("my-mentor/reviews/", MyMentorReviewView.as_view(), name="my-mentor-review"),
    path("my-mentor/request/", MentorRequestView.as_view(), name="my-mentor-request"),
]