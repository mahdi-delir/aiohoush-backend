from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from aiohoush.core.responses import APIResponse

from .models import Announcement
from .services import announcements as service


PAGE_SIZE = 20


def _ok(message, data=None, http_status=status.HTTP_200_OK):
    return APIResponse(success=True, called_by="webapp", message=message, data=data, status=http_status)


def _failure(message):
    return APIResponse(success=False, called_by="webapp", message=message, status=status.HTTP_200_OK)


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _int_list(value) -> list[int]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        number = _int(item)
        if number is not None:
            result.append(number)
    return result


def _inbox_row(recipient) -> dict:
    announcement = recipient.announcement
    return {
        "id": announcement.pk,
        "title": announcement.title,
        "body": announcement.body,
        "link": announcement.link or None,
        "sender": service.sender_label(announcement),
        "createdAt": recipient.created_at.isoformat(),
        "read": recipient.read_at is not None,
    }


# --- صندوق اعلان‌های کاربر ---------------------------------------------------------

class InboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = service.inbox(request.user)
        total = items.count()
        page_count = max(1, -(-total // PAGE_SIZE))
        page = min(max(1, _int(request.query_params.get("page"), 1)), page_count)
        start = (page - 1) * PAGE_SIZE

        return _ok(
            "اعلان‌ها دریافت شد.",
            {
                "items": [_inbox_row(item) for item in items[start:start + PAGE_SIZE]],
                "unreadCount": service.unread_count(request.user),
                "page": page,
                "pageCount": page_count,
            },
        )


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return _ok("تعداد اعلان‌های خوانده‌نشده.", {"unreadCount": service.unread_count(request.user)})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, announcement_id):
        if not service.mark_read(user=request.user, announcement_id=announcement_id):
            return _failure("اعلان پیدا نشد.")
        return _ok("خوانده شد.", {"unreadCount": service.unread_count(request.user)})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        service.mark_all_read(request.user)
        return _ok("همه خوانده شد.", {"unreadCount": 0})


# --- ارسال (برای پنل‌های استاد، فروشنده و مدیریت) ---------------------------------------

class ComposeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request):
        options = service.compose_options(request.user)
        if not options["audiences"]:
            return _failure("اجازهٔ ارسال اعلان را ندارید.")
        return _ok("گزینه‌های ارسال اعلان.", options)

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        try:
            announcement = service.create_and_publish(
                sender=request.user,
                data=service.AnnouncementInput(
                    title=str(data.get("title") or ""),
                    body=str(data.get("body") or ""),
                    audience=str(data.get("audience") or ""),
                    link=str(data.get("link") or ""),
                    group_ids=_int_list(data.get("groups")),
                    user_ids=_int_list(data.get("users")),
                    course_ids=_int_list(data.get("courses")),
                    mentor_id=_int(data.get("mentor")),
                    send_sms=data.get("send_sms") is True,
                ),
            )
        except service.AnnouncementError as exc:
            return _failure(str(exc))

        return _ok(
            f"اعلان برای {announcement.recipient_count:,} نفر ارسال شد.",
            {"id": announcement.pk, "recipientCount": announcement.recipient_count},
            status.HTTP_201_CREATED,
        )


class SentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Q

        sent = (
            Announcement.objects
            .filter(created_by=request.user)
            .annotate(read_count=Count("recipients", filter=Q(recipients__read_at__isnull=False)))
            .order_by("-created_at")[:100]
        )
        return _ok(
            "اعلان‌های ارسالی.",
            {
                "items": [
                    {
                        "id": item.pk,
                        "title": item.title,
                        "audience": item.audience,
                        "audienceLabel": item.get_audience_display(),
                        "recipientCount": item.recipient_count,
                        "readCount": item.read_count,
                        "sendSms": item.send_sms,
                        "createdAt": item.created_at.isoformat(),
                    }
                    for item in sent
                ],
            },
        )
