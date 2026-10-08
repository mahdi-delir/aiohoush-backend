"""ثبت تماشای ویدئوهای هدیه.

همان قواعد جلسات دوره (course/services/watch.py): بازه‌های پخش‌شده ادغام
می‌شوند، مجموع زمان جدید هر batch به زمان واقعی سپری‌شده محدود است و
با ۹۰٪ زمان مشاهدهٔ یکتا، ویدئو «دیده‌شده» ثبت می‌شود.

«هدیه را دیده» = همهٔ ویدئوهای هدیهٔ فعال و عمومی را دیده باشد.
"""

import uuid
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from course.models import GiftVideo, GiftVideoProgress
from course.services.watch import (
    COMPLETION_RATIO,
    _clip_ranges,
    merge_ranges,
    remaining_budget_ms,
)


@dataclass(frozen=True, slots=True)
class GiftWatchState:
    watched_percent: int
    completed: bool


def visible_gifts():
    return GiftVideo.objects.filter(is_active=True, is_public=True)


def has_watched_all_gifts(user) -> bool:
    gift_ids = set(visible_gifts().values_list("pk", flat=True))

    # بدون ویدئوی هدیه، کاربر را به صفحهٔ خالی هدیه‌ها نمی‌فرستیم.
    if not gift_ids:
        return True

    completed = set(
        GiftVideoProgress.objects
        .filter(user=user, gift_id__in=gift_ids, completed_at__isnull=False)
        .values_list("gift_id", flat=True)
    )
    return completed == gift_ids


def gift_duration_ms(gift: GiftVideo) -> int | None:
    if gift.duration and gift.duration.total_seconds() > 0:
        return int(gift.duration.total_seconds() * 1000)

    return None


def _percent(progress: GiftVideoProgress, duration_ms: int | None) -> int:
    if progress.completed_at:
        return 100
    if not duration_ms:
        return 0
    return min(99, int(progress.unique_watched_ms * 100 / duration_ms))


@transaction.atomic
def start_gift_watch(*, user, gift: GiftVideo) -> GiftVideoProgress:
    progress, _ = GiftVideoProgress.objects.get_or_create(user=user, gift=gift)
    progress = GiftVideoProgress.objects.select_for_update().get(pk=progress.pk)

    now = timezone.now()
    progress.watch_token = uuid.uuid4()
    progress.watch_started_at = now
    progress.watch_credited_ms = 0
    progress.last_activity_at = now
    progress.save(update_fields=[
        "watch_token", "watch_started_at", "watch_credited_ms",
        "last_activity_at", "updated_at",
    ])

    return progress


@transaction.atomic
def record_gift_batch(
    *,
    progress_id: int,
    ranges: list[tuple[int, int]],
    position_ms: int,
    ended: bool,
    end_reason: str | None,
) -> GiftWatchState:
    progress = (
        GiftVideoProgress.objects
        .select_for_update()
        .select_related("gift")
        .get(pk=progress_id)
    )
    duration_ms = gift_duration_ms(progress.gift)
    now = timezone.now()

    budget_ms = remaining_budget_ms(
        started_at=progress.watch_started_at or progress.last_activity_at or progress.created_at,
        credited_ms=progress.watch_credited_ms,
        now=now,
    )

    accepted, credited_ms = _clip_ranges(
        merge_ranges(ranges),
        duration_ms=duration_ms,
        budget_ms=budget_ms,
    )

    progress.watch_credited_ms += credited_ms

    if accepted:
        existing = [tuple(item) for item in progress.watched_ranges]
        merged = merge_ranges(existing + accepted)
        progress.watched_ranges = [list(item) for item in merged]
        progress.unique_watched_ms = sum(end - start for start, end in merged)

    if duration_ms:
        position_ms = min(position_ms, duration_ms)

    # بعد از پایان ویدئو، دفعهٔ بعد از ابتدا پخش شود.
    progress.last_position_ms = 0 if ended else position_ms
    progress.last_activity_at = now

    if (
        progress.completed_at is None
        and duration_ms
        and progress.unique_watched_ms >= duration_ms * COMPLETION_RATIO
    ):
        progress.completed_at = now

    # پایان نوبت تماشا: play بعدی نوبت جدید می‌سازد.
    if ended or end_reason:
        progress.watch_token = None

    progress.save(update_fields=[
        "watched_ranges", "unique_watched_ms", "last_position_ms",
        "last_activity_at", "completed_at", "watch_token",
        "watch_credited_ms", "updated_at",
    ])

    return GiftWatchState(
        watched_percent=_percent(progress, duration_ms),
        completed=progress.completed_at is not None,
    )
