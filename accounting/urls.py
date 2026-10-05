from django.urls import path

from .views import MentorLeaderboardView, WalletTopUpReturnView, WalletTopUpView, WalletView


urlpatterns = [
    path(
        "wallet/",
        WalletView.as_view(),
        name="wallet",
    ),
    path(
        "wallet/top-up/",
        WalletTopUpView.as_view(),
        name="wallet-top-up",
    ),
    path(
        "wallet/top-up/payment-return/",
        WalletTopUpReturnView.as_view(),
        name="wallet-top-up-return",
    ),
    path(
        "mentor-leaderboard/",
        MentorLeaderboardView.as_view(),
        name="mentor-leaderboard",
    ),
]
