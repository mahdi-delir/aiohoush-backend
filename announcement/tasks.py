import logging

from celery import shared_task


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def send_announcement_sms(*, announcement_id: int) -> None:
    """پیامک اعلان به همهٔ گیرندگان (در batch های سرویس پیامک)."""
    from announcement.models import Announcement
    from announcement.services.announcements import sms_text
    from notification.models import SMSServerResponse
    from notification.services.sms import OutgoingSMS, prepare_sms_messages, send_sms_requests

    announcement = Announcement.objects.filter(pk=announcement_id).first()
    if announcement is None or not announcement.send_sms:
        return

    mobiles = list(
        announcement.recipients
        .filter(user__is_active=True)
        .values_list("user__mobile", flat=True)
    )
    if not mobiles:
        return

    text = sms_text(announcement)
    prepared = prepare_sms_messages(
        messages=[OutgoingSMS(recipient=mobile, text=text) for mobile in mobiles],
    )
    results = send_sms_requests(messages=prepared)

    failed = [result for result in results if result.status != SMSServerResponse.SMSSTATUS.SENT]
    if failed:
        logger.warning(
            "Announcement SMS partially failed. announcement=%s failed_batches=%s/%s",
            announcement.pk, len(failed), len(results),
        )


@shared_task(ignore_result=True)
def send_announcement_push(*, announcement_id: int) -> None:
    """نوتیفیکیشن روی گوشی برای همهٔ گیرندگانی که آن را فعال کرده‌اند."""
    from announcement.models import Announcement
    from announcement.services import push

    announcement = Announcement.objects.filter(pk=announcement_id).first()
    if announcement is None or not push.is_enabled():
        return

    link = announcement.link
    url = link if link.startswith("/") and not link.startswith("//") else "/dashboard/notifications"
    body = " ".join(announcement.body.split())
    if len(body) > 180:
        body = body[:180].rsplit(" ", 1)[0] + "…"

    sent, total = push.send_to_users(
        user_ids=announcement.recipients.values_list("user_id", flat=True),
        title=announcement.title,
        body=body,
        url=url,
        tag=f"announcement-{announcement.pk}",
    )
    logger.info("Announcement push. announcement=%s sent=%s/%s", announcement.pk, sent, total)
