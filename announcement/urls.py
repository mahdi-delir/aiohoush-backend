from django.urls import path

from .views import ComposeView, InboxView, MarkAllReadView, MarkReadView, SentView, UnreadCountView


urlpatterns = [
    path("", InboxView.as_view(), name="announcement-inbox"),
    path("unread-count/", UnreadCountView.as_view(), name="announcement-unread-count"),
    path("read-all/", MarkAllReadView.as_view(), name="announcement-read-all"),
    path("<int:announcement_id>/read/", MarkReadView.as_view(), name="announcement-read"),
    path("compose/", ComposeView.as_view(), name="announcement-compose"),
    path("sent/", SentView.as_view(), name="announcement-sent"),
]
