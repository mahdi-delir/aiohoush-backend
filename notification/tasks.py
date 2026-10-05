from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from notification.models import OTPSMSToken, SMSServerResponse
from notification.services.otp import create_otp
from notification.services.sms import (
    OutgoingSMS,
    prepare_sms_messages,
    send_sms_requests,
)

logger = get_task_logger(__name__)

User = get_user_model()

@shared_task(
    ignore_result = True
)
def send_otp_sms(
    *,
    user_id: int,
    reason: str,
) -> None:
    
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(
            _("OTP SMS task skipped because user does not exist. user_id=%s"),
            user_id,
        )
        return

    if reason not in OTPSMSToken.OTPREASON.values:
        raise ValueError(_("Invalid OTP reason."))

    otp, raw_code = create_otp(
        user=user,
        reason=reason,
        length=settings.OTP_LENGTH,
    )

    text = f'کد تأیید شما: {raw_code}\nآیوهوش - برترین پلتفرم آموزش برنامه نویسی و هوش مصنوعی'

    outgoing_message = OutgoingSMS(
        recipient=user.mobile,
        text=text,
        otp=otp,
    )

    prepared_messages = prepare_sms_messages(
        messages=[outgoing_message],
    )

    results = send_sms_requests(
        messages=prepared_messages,
    )

    result = results[0]

    if result.status != SMSServerResponse.SMSSTATUS.SENT:
        logger.warning(
            _("OTP SMS sending did not succeed. user_id=%s user=%s otp_id=%s trace_ids=%s status=%s"),
            user.pk,
            user,
            otp.pk,
            result.trace_ids,
            result.status,
        )

@shared_task(ignore_result=True)
def send_welcome_sms(
    *,
    user_id: int,
) -> None:
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(
            _("Welcome SMS task skipped because user does not exist. user_id=%s"),
            user_id,
        )
        return

    text = f'به آیوهوش خوش آمدید!\nحساب کاربری شما با موفقیت در آیوهوش ایجاد شد.\nآیوهوش برترین پلتفرم آموزش برنامه نویسی و هوش مصنوعی.\nhttps://aiohoush.com'

    outgoing_message = OutgoingSMS(
        recipient=user.mobile,
        text=text,
    )

    prepared_messages = prepare_sms_messages(
        messages=[outgoing_message],
    )

    results = send_sms_requests(
        messages=prepared_messages,
    )

    result = results[0]

    if result.status != SMSServerResponse.SMSSTATUS.SENT:
        logger.warning(
            _("Welcome SMS sending did not succeed. user_id=%s user=%s trace_ids=%s status=%s"),
            user.pk,
            user,
            result.trace_ids,
            result.status,
        )


@shared_task(ignore_result=True)
def send_ticket_sms(
    *,
    ticket_id: int,
    event: str,
) -> None:
    from ticket.models import Ticket

    ticket = (
        Ticket.objects
        .select_related("student")
        .filter(pk=ticket_id)
        .first()
    )

    if ticket is None:
        logger.warning("Ticket SMS skipped; ticket %s not found.", ticket_id)
        return

    link = f"{settings.APP_ORIGIN.rstrip('/')}/dashboard/tickets/{ticket.pk}"

    if event == "created":
        text = (
            f"تیکت شما با شماره {ticket.pk} در آیوهوش ثبت شد و به‌زودی پاسخ داده می‌شود.\n{link}"
        )
    elif event == "answered":
        text = f"به تیکت شماره {ticket.pk} شما در آیوهوش پاسخ داده شد.\n{link}"
    else:
        raise ValueError(f"Unknown ticket SMS event: {event}")

    prepared_messages = prepare_sms_messages(
        messages=[
            OutgoingSMS(
                recipient=ticket.student.mobile,
                text=text,
            )
        ],
    )

    result = send_sms_requests(messages=prepared_messages)[0]

    if result.status != SMSServerResponse.SMSSTATUS.SENT:
        logger.warning(
            "Ticket SMS not sent. ticket=%s event=%s status=%s",
            ticket.pk,
            event,
            result.status,
        )


@shared_task(ignore_result=True)
def close_stale_tickets_task() -> None:
    """برای اجرای دوره‌ای (celery beat یا cron)."""
    from ticket.services.tickets import close_stale_tickets

    closed = close_stale_tickets()
    if closed:
        logger.info("Closed %s stale tickets.", closed)
