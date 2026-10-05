from pathlib import Path

from django.db.models import Prefetch
from django.http import FileResponse, Http404

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse
from user.services.mentor import full_name

from .models import Ticket, TicketMessage
from .services import tickets as ticket_service


def _failure(message):
    return APIResponse(
        success=False,
        called_by="webapp",
        message=message,
        status=status.HTTP_200_OK,
    )


def _file_url(message, kind):
    return f"/ticket/files/{message.pk}/{kind}/"


def _message_row(message, viewer):
    return {
        "id": message.pk,
        "isMine": message.author_id == viewer.pk,
        "authorName": full_name(message.author),
        "text": message.text,
        "attachment": (
            {
                "name": message.attachment_name or Path(message.attachment.name).name,
                "url": _file_url(message, "attachment"),
            }
            if message.attachment
            else None
        ),
        "voice": (
            {
                "url": _file_url(message, "voice"),
                "durationMs": message.voice_duration_ms,
            }
            if message.voice
            else None
        ),
        "createdAt": message.created_at.isoformat(),
    }


def _ticket_row(ticket):
    return {
        "id": ticket.pk,
        "subject": ticket.subject,
        "department": ticket.department,
        "departmentLabel": ticket.get_department_display(),
        "recipient": ticket_service.recipient_label(ticket),
        "courseTitle": ticket.course.title if ticket.course_id else None,
        "status": ticket.status,
        "statusLabel": ticket.get_status_display(),
        "lastMessageAt": ticket.last_message_at.isoformat(),
        "createdAt": ticket.created_at.isoformat(),
    }


def _optional_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class TicketListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        own = Ticket.objects.filter(student=request.user)
        ticket_service.close_stale_tickets(own)

        tickets = own.select_related("assigned_to", "course").order_by("-last_message_at")

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تیکت‌ها دریافت شد.",
            data={"tickets": [_ticket_row(ticket) for ticket in tickets]},
        )

    def post(self, request):
        try:
            ticket = ticket_service.create_ticket(
                student=request.user,
                department=str(request.data.get("department", "")),
                course_id=request.data.get("course"),
                subject=str(request.data.get("subject", "")),
                text=str(request.data.get("text", "")),
                attachment=request.FILES.get("attachment"),
                voice=request.FILES.get("voice"),
                voice_duration_ms=_optional_int(request.data.get("voice_duration_ms")),
            )
        except ticket_service.TicketError as exc:
            return _failure(str(exc))

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تیکت شما ثبت شد.",
            data=_ticket_row(ticket),
            status=status.HTTP_201_CREATED,
        )


class TicketOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return APIResponse(
            success=True,
            called_by="webapp",
            message="گزینه‌های تیکت دریافت شد.",
            data=ticket_service.department_options(request.user),
        )


def _own_ticket(request, ticket_id):
    return (
        Ticket.objects
        .filter(pk=ticket_id, student=request.user)
        .select_related("assigned_to", "course")
        .first()
    )


class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        ticket_service.close_stale_tickets(
            Ticket.objects.filter(pk=ticket_id, student=request.user)
        )

        ticket = (
            Ticket.objects
            .filter(pk=ticket_id, student=request.user)
            .select_related("assigned_to", "course")
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=TicketMessage.objects.select_related("author"),
                )
            )
            .first()
        )

        if ticket is None:
            return _failure("تیکت پیدا نشد.")

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تیکت دریافت شد.",
            data={
                **_ticket_row(ticket),
                "messages": [
                    _message_row(message, request.user)
                    for message in ticket.messages.all()
                ],
            },
        )


class TicketMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, ticket_id):
        if _own_ticket(request, ticket_id) is None:
            return _failure("تیکت پیدا نشد.")

        try:
            message = ticket_service.add_message(
                ticket_id=ticket_id,
                author=request.user,
                text=str(request.data.get("text", "")),
                attachment=request.FILES.get("attachment"),
                voice=request.FILES.get("voice"),
                voice_duration_ms=_optional_int(request.data.get("voice_duration_ms")),
            )
        except ticket_service.TicketError as exc:
            return _failure(str(exc))

        return APIResponse(
            success=True,
            called_by="webapp",
            message="پیام ارسال شد.",
            data=_message_row(message, request.user),
            status=status.HTTP_201_CREATED,
        )


class TicketCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        if _own_ticket(request, ticket_id) is None:
            return _failure("تیکت پیدا نشد.")

        try:
            ticket = ticket_service.close_ticket(ticket_id=ticket_id, by=request.user)
        except ticket_service.TicketError as exc:
            return _failure(str(exc))

        return APIResponse(
            success=True,
            called_by="webapp",
            message="تیکت بسته شد.",
            data=_ticket_row(ticket),
        )


class TicketFileView(APIView):
    """دانلود پیوست یا پخش پیام صوتی؛ فقط برای صاحب تیکت (و superuser)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, message_id, kind):
        if kind not in {"attachment", "voice"}:
            raise Http404

        message = (
            TicketMessage.objects
            .select_related("ticket")
            .filter(pk=message_id)
            .first()
        )

        if message is None or not (
            message.ticket.student_id == request.user.pk
            or request.user.is_superuser
        ):
            return _failure("فایل پیدا نشد.")

        field = getattr(message, kind)
        if not field:
            return _failure("فایل پیدا نشد.")

        try:
            handle = field.open("rb")
        except FileNotFoundError:
            raise Http404("فایل روی سرور پیدا نشد.")

        if kind == "voice":
            # برای پخش در <audio> به‌صورت inline
            return FileResponse(handle)

        return FileResponse(
            handle,
            as_attachment=True,
            filename=message.attachment_name or Path(field.name).name,
        )
