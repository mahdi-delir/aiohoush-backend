from django.contrib import admin, messages

from .models import Ticket, TicketMessage
from .services import tickets as ticket_service


class TicketMessageInline(admin.StackedInline):
    """پیام‌های قبلی فقط‌خواندنی؛ ردیف خالی = ارسال پاسخ.

    تا ساخته شدن پنل پشتیبانی، پاسخ از اینجا هم ممکن است. پاسخ از همان
    سرویس تیکت ثبت می‌شود (وضعیت «پاسخ داده شده» + پیامک به دانشجو).
    """

    model = TicketMessage
    extra = 1
    fields = ("author", "text", "attachment", "voice", "created_at")
    readonly_fields = ("author", "created_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "student", "department", "assigned_to", "status", "last_message_at")
    list_filter = ("status", "department", "last_message_at")
    search_fields = ("id", "subject", "student__mobile", "student__last_name")
    list_select_related = ("student", "assigned_to")
    readonly_fields = (
        "student", "department", "assigned_to", "course", "subject",
        "status", "last_message_at", "closed_at", "closed_by", "created_at",
    )
    inlines = (TicketMessageInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_formset(self, request, form, formset, change):
        if formset.model is not TicketMessage:
            return super().save_formset(request, form, formset, change)

        for message_form in formset.forms:
            if not message_form.has_changed() or message_form.instance.pk:
                continue

            data = message_form.cleaned_data
            try:
                ticket_service.add_message(
                    ticket_id=form.instance.pk,
                    author=request.user,
                    text=data.get("text") or "",
                    attachment=data.get("attachment"),
                    voice=data.get("voice"),
                )
            except ticket_service.TicketError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
