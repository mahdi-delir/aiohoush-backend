"""ثبت پیشرفت تماشای ویدئوی جلسات.

جریان کار:
1. پلیر روی اولین play، یک «نوبت تماشا» (CourseSessionWatch) می‌سازد
   و موقعیت ادامهٔ پخش را می‌گیرد.
2. هر چند ثانیه یک batch می‌فرستد: رویدادها (play/pause/seek/...) و
   بازه‌هایی از ویدئو که واقعاً پخش شده‌اند.
3. سرور بازه‌ها را با بازه‌های قبلی ادغام می‌کند؛ «زمان مشاهدهٔ یکتا»
   مجموع بازه‌های ادغام‌شده است. وقتی به آستانهٔ تکمیل برسد، جلسه
   تکمیل‌شده ثبت می‌شود.

بازه‌ها را کلاینت گزارش می‌کند، پس مجموع زمان جدید هر batch به زمان
واقعی سپری‌شده (ضرب در حداکثر سرعت پخش) محدود می‌شود تا نتوان با یک
درخواست کل ویدئو را «دیده‌شده» ثبت کرد.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from course.models import (
    CourseSession,
    CourseSessionProgress,
    CourseSessionWatch,
    CourseSessionWatchedRange,
    CourseSessionWatchEvent,
)


# بخشی از ویدئو که باید یکتا دیده شود تا جلسه تکمیل حساب شود.
COMPLETION_RATIO = 0.9

# بیشترین سرعت پخش مجاز در پلیر + حاشیهٔ تأخیر شبکه
MAX_PLAYBACK_RATE = 2.0
BUDGET_SLACK = timedelta(seconds=20)

@dataclass(frozen=True, slots=True)
class WatchState:
    unique_watched_ms: int
    watched_percent: int
    last_position_ms: int
    completed: bool


def session_duration_ms(
    session: CourseSession,
) -> int | None:
    if session.duration and session.duration.total_seconds() > 0:
        return int(session.duration.total_seconds() * 1000)

    return None


def remaining_budget_ms(*, started_at, credited_ms: int, now) -> int:
    elapsed = (now - started_at) + BUDGET_SLACK
    allowed = int(elapsed.total_seconds() * 1000 * MAX_PLAYBACK_RATE)
    return max(0, allowed - credited_ms)


def progress_percent(
    progress: CourseSessionProgress | None,
    duration_ms: int | None,
) -> int:
    if progress is None:
        return 0

    if progress.completed_at:
        return 100

    if not duration_ms:
        return 0

    return min(
        99,
        int(progress.unique_watched_ms * 100 / duration_ms),
    )


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []

    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return [(start, end) for start, end in merged]


def _clip_ranges(
    ranges: list[tuple[int, int]],
    *,
    duration_ms: int | None,
    budget_ms: int,
) -> tuple[list[tuple[int, int]], int]:
    """بازه‌ها را به [0, duration] محدود و مجموعشان را به budget کوتاه می‌کند."""
    clipped: list[tuple[int, int]] = []
    used = 0

    for start, end in ranges:
        if duration_ms:
            end = min(end, duration_ms)

        if end <= start:
            continue

        remaining = budget_ms - used
        if remaining <= 0:
            break

        end = min(end, start + remaining)
        clipped.append((start, end))
        used += end - start

    return clipped, used


@transaction.atomic
def start_watch(
    *,
    user,
    session: CourseSession,
    auth_session_id: str | None,
) -> tuple[CourseSessionWatch, CourseSessionProgress]:
    progress, _ = CourseSessionProgress.objects.get_or_create(
        user=user,
        session=session,
    )

    progress = (
        CourseSessionProgress.objects
        .select_for_update()
        .get(pk=progress.pk)
    )

    # نوبت‌های قبلی که بسته نشده‌اند (مثلاً تب بسته شده) پایان می‌یابند.
    CourseSessionWatch.objects.filter(
        progress=progress,
        ended_at__isnull=True,
    ).update(
        ended_at=timezone.now(),
        end_reason=CourseSessionWatch.ENDREASON.UNKNOWN,
    )

    watch = CourseSessionWatch.objects.create(
        progress=progress,
        auth_session_id=auth_session_id,
        start_position_ms=progress.last_position_ms,
        last_position_ms=progress.last_position_ms,
        max_position_ms=progress.last_position_ms,
    )

    CourseSessionProgress.objects.filter(pk=progress.pk).update(
        watch_count=F("watch_count") + 1,
        last_watched_at=timezone.now(),
    )
    progress.refresh_from_db()

    return watch, progress


@transaction.atomic
def record_watch_batch(
    *,
    watch: CourseSessionWatch,
    events: list[dict],
    ranges: list[tuple[int, int]],
    position_ms: int,
    end_reason: str | None,
) -> WatchState | None:
    """یک batch را ثبت می‌کند. None یعنی نوبت تماشا قبلاً بسته شده."""
    watch = (
        CourseSessionWatch.objects
        .select_for_update()
        .select_related("progress__session")
        .get(pk=watch.pk)
    )
    progress = (
        CourseSessionProgress.objects
        .select_for_update()
        .get(pk=watch.progress_id)
    )
    session = watch.progress.session
    duration_ms = session_duration_ms(session)

    if watch.ended_at is not None:
        return None

    now = timezone.now()

    # --- رویدادها (idempotent بر اساس client_event_id)
    event_ids = [event["client_event_id"] for event in events]
    existing_ids = set(
        CourseSessionWatchEvent.objects
        .filter(client_event_id__in=event_ids)
        .values_list("client_event_id", flat=True)
    )
    new_events = [
        event for event in events
        if event["client_event_id"] not in existing_ids
    ]

    # تکرار همان batch (مثلاً retry بعد از قطعی شبکه): چیزی دوباره
    # شمرده نمی‌شود.
    if events and not new_events:
        return _state(progress, duration_ms)

    CourseSessionWatchEvent.objects.bulk_create(
        [
            CourseSessionWatchEvent(
                watch=watch,
                sequence=event["sequence"],
                client_event_id=event["client_event_id"],
                event_type=event["event_type"],
                position_ms=event["position_ms"],
                from_position_ms=event.get("from_position_ms"),
                to_position_ms=event.get("to_position_ms"),
                playback_rate=event.get("playback_rate"),
                client_occurred_at=event.get("occurred_at"),
            )
            for event in new_events
        ],
        ignore_conflicts=True,
    )

    play_count = sum(
        1 for event in new_events
        if event["event_type"] == CourseSessionWatchEvent.EVENT.PLAY
    )

    # --- بازه‌های دیده‌شده، محدود به زمان واقعی سپری‌شده
    budget_ms = remaining_budget_ms(
        started_at=watch.started_at,
        credited_ms=watch.watched_ms,
        now=now,
    )

    accepted, watched_ms = _clip_ranges(
        merge_ranges(ranges),
        duration_ms=duration_ms,
        budget_ms=budget_ms,
    )

    if accepted:
        existing = list(
            progress.watched_ranges.values_list("start_ms", "end_ms")
        )
        merged = merge_ranges(existing + accepted)

        progress.watched_ranges.all().delete()
        CourseSessionWatchedRange.objects.bulk_create(
            [
                CourseSessionWatchedRange(
                    progress=progress,
                    start_ms=start,
                    end_ms=end,
                )
                for start, end in merged
            ]
        )

        progress.unique_watched_ms = sum(end - start for start, end in merged)
        furthest = max(end for _, end in accepted)
        progress.max_position_ms = max(progress.max_position_ms, furthest)
        watch.max_position_ms = max(watch.max_position_ms, furthest)

    if duration_ms:
        position_ms = min(position_ms, duration_ms)

    ended = any(
        event["event_type"] == CourseSessionWatchEvent.EVENT.ENDED
        for event in new_events
    )

    # بعد از پایان ویدئو، دفعهٔ بعد از ابتدا پخش شود.
    progress.last_position_ms = 0 if ended else position_ms
    progress.total_watched_ms += watched_ms
    progress.play_count += play_count
    progress.last_watched_at = now

    if (
        progress.completed_at is None
        and duration_ms
        and progress.unique_watched_ms >= duration_ms * COMPLETION_RATIO
    ):
        progress.completed_at = now

    progress.save(
        update_fields=[
            "unique_watched_ms",
            "max_position_ms",
            "last_position_ms",
            "total_watched_ms",
            "play_count",
            "last_watched_at",
            "completed_at",
            "updated_at",
        ]
    )

    watch.last_position_ms = position_ms
    watch.watched_ms += watched_ms

    if ended:
        end_reason = CourseSessionWatch.ENDREASON.ENDED

    if end_reason:
        watch.ended_at = now
        watch.end_reason = end_reason

    watch.save(
        update_fields=[
            "last_position_ms",
            "max_position_ms",
            "watched_ms",
            "ended_at",
            "end_reason",
        ]
    )

    return _state(progress, duration_ms)


def _state(
    progress: CourseSessionProgress,
    duration_ms: int | None,
) -> WatchState:
    return WatchState(
        unique_watched_ms=progress.unique_watched_ms,
        watched_percent=progress_percent(progress, duration_ms),
        last_position_ms=progress.last_position_ms,
        completed=progress.completed_at is not None,
    )
