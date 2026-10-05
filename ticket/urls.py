from django.urls import path

from .views import (
    TicketCloseView,
    TicketDetailView,
    TicketFileView,
    TicketListCreateView,
    TicketMessageCreateView,
    TicketOptionsView,
)


urlpatterns = [
    path("", TicketListCreateView.as_view(), name="tickets"),
    path("options/", TicketOptionsView.as_view(), name="ticket-options"),
    path("<int:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("<int:ticket_id>/messages/", TicketMessageCreateView.as_view(), name="ticket-messages"),
    path("<int:ticket_id>/close/", TicketCloseView.as_view(), name="ticket-close"),
    path("files/<int:message_id>/<str:kind>/", TicketFileView.as_view(), name="ticket-file"),
]
