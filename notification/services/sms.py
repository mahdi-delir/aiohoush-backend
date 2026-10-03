import requests

from dataclasses import dataclass
from typing import Sequence

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from notification.models import OTPSMSToken, SMSServerResponse


PAYAMRESAN_MAX_MESSAGES_PER_REQUEST = 90


@dataclass(frozen=True, slots=True)
class OutgoingSMS:
    recipient: str
    text: str
    otp: OTPSMSToken | None = None


@dataclass(frozen=True, slots=True)
class PreparedSMS:
    recipient: str
    text: str
    trace_id: int


@dataclass(frozen=True, slots=True)
class SMSBatchResult:
    trace_ids: tuple[int, ...]
    status: str
    http_status: int | None


@transaction.atomic
def prepare_sms_messages(
    *,
    messages: Sequence[OutgoingSMS],
) -> list[PreparedSMS]:
    if not messages:
        raise ValueError(
            _("حداقل یک پیام برای ارسال لازم است.")
        )

    sms_objects = [
        SMSServerResponse(
            otp=message.otp,
            text=(
                _("پیام حاوی کد یکبار مصرف")
                if message.otp is not None
                else message.text
            ),
            recipient=message.recipient,
            status=SMSServerResponse.SMSSTATUS.REQUESTED,
        )
        for message in messages
    ]

    for sms_object in sms_objects:
        sms_object.full_clean(exclude={"trace_id"})

    created_objects = SMSServerResponse.objects.bulk_create(
        sms_objects
    )

    return [
        PreparedSMS(
            recipient=message.recipient,
            text=message.text,
            trace_id=sms_object.trace_id,
        )
        for message, sms_object in zip(
            messages,
            created_objects,
            strict=True,
        )
    ]


def _update_batch_status(
    *,
    batch: Sequence[PreparedSMS],
    status: str,
    server_response: dict,
) -> None:
    trace_ids = [
        message.trace_id
        for message in batch
    ]

    SMSServerResponse.objects.filter(
        trace_id__in=trace_ids,
    ).update(
        status=status,
        server_response=server_response,
        updated_at=timezone.now(),
    )


def _parse_response(
    response: requests.Response,
) -> tuple[object | None, dict]:
    try:
        body = response.json()

        stored_response = {
            "http_status": response.status_code,
            "body": body,
        }

        return body, stored_response

    except requests.exceptions.JSONDecodeError:
        return None, {
            "http_status": response.status_code,
            "raw_body": response.text,
        }


def send_sms_requests(
    *,
    messages: Sequence[PreparedSMS],
) -> list[SMSBatchResult]:
    if not messages:
        raise ValueError(
            _("حداقل یک پیام برای ارسال لازم است.")
        )

    results: list[SMSBatchResult] = []

    with requests.Session() as session:
        for start in range(
            0,
            len(messages),
            PAYAMRESAN_MAX_MESSAGES_PER_REQUEST,
        ):
            batch = messages[
                start:start + PAYAMRESAN_MAX_MESSAGES_PER_REQUEST
            ]

            trace_ids = tuple(
                message.trace_id
                for message in batch
            )

            payload = {
                "ApiKey": settings.PAYAMRESAN_API_KEY,
                "Recipients": [
                    {
                        "Sender": settings.PAYAMRESAN_SENDER,
                        "Text": message.text,
                        "Destination": message.recipient,
                        "UserTraceId": message.trace_id,
                    }
                    for message in batch
                ],
            }

            try:
                response = session.post(
                    settings.PAYAMRESAN_API_URL,
                    json=payload,
                    timeout=(
                        settings.SMS_CONNECT_TIMEOUT,
                        settings.SMS_READ_TIMEOUT,
                    ),
                )

            except requests.exceptions.ConnectTimeout:
                _update_batch_status(
                    batch=batch,
                    status=SMSServerResponse.SMSSTATUS.TIMEOUT,
                    server_response={
                        "error_type": "ConnectTimeout",
                    },
                )

                results.append(
                    SMSBatchResult(
                        trace_ids=trace_ids,
                        status=SMSServerResponse.SMSSTATUS.TIMEOUT,
                        http_status=None,
                    )
                )

                continue

            except requests.exceptions.ReadTimeout:
                _update_batch_status(
                    batch=batch,
                    status=SMSServerResponse.SMSSTATUS.TIMEOUT,
                    server_response={
                        "error_type": "ReadTimeout",
                    },
                )

                results.append(
                    SMSBatchResult(
                        trace_ids=trace_ids,
                        status=SMSServerResponse.SMSSTATUS.TIMEOUT,
                        http_status=None,
                    )
                )

                continue

            except requests.exceptions.ConnectionError:
                _update_batch_status(
                    batch=batch,
                    status=SMSServerResponse.SMSSTATUS.FAILED,
                    server_response={
                        "error_type": "ConnectionError",
                    },
                )

                results.append(
                    SMSBatchResult(
                        trace_ids=trace_ids,
                        status=SMSServerResponse.SMSSTATUS.FAILED,
                        http_status=None,
                    )
                )

                continue

            except requests.exceptions.RequestException as exc:
                _update_batch_status(
                    batch=batch,
                    status=SMSServerResponse.SMSSTATUS.FAILED,
                    server_response={
                        "error_type": exc.__class__.__name__,
                    },
                )

                results.append(
                    SMSBatchResult(
                        trace_ids=trace_ids,
                        status=SMSServerResponse.SMSSTATUS.FAILED,
                        http_status=None,
                    )
                )

                continue

            parsed_body, stored_response = _parse_response(
                response
            )

            try:
                response.raise_for_status()

            except requests.exceptions.HTTPError:
                _update_batch_status(
                    batch=batch,
                    status=SMSServerResponse.SMSSTATUS.FAILED,
                    server_response=stored_response,
                )

                results.append(
                    SMSBatchResult(
                        trace_ids=trace_ids,
                        status=SMSServerResponse.SMSSTATUS.FAILED,
                        http_status=response.status_code,
                    )
                )

                continue

            if not isinstance(parsed_body, dict):
                status = SMSServerResponse.SMSSTATUS.FAILED

            elif parsed_body.get("Success") is True:
                status = SMSServerResponse.SMSSTATUS.SENT

            elif parsed_body.get("Success") is False:
                status = SMSServerResponse.SMSSTATUS.REJECTED

            else:
                status = SMSServerResponse.SMSSTATUS.FAILED

            _update_batch_status(
                batch=batch,
                status=status,
                server_response=stored_response,
            )

            results.append(
                SMSBatchResult(
                    trace_ids=trace_ids,
                    status=status,
                    http_status=response.status_code,
                )
            )

    return results