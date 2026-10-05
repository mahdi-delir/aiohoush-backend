"""دورهٔ ماهانهٔ حسابرسی (ماه شمسی، از روز قابل تنظیم)."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from accounting.models import AccountingSettings
from aiohoush.utilities.jalali import (
    PERSIAN_MONTHS,
    add_jalali_months,
    gregorian_to_jalali,
    jalali_to_gregorian,
    to_persian_digits,
)


TEHRAN = ZoneInfo("Asia/Tehran")


@dataclass(frozen=True, slots=True)
class Period:
    start: datetime
    end: datetime
    jy: int
    jm: int
    start_day: int

    @property
    def label(self) -> str:
        month = PERSIAN_MONTHS[self.jm - 1]

        if self.start_day == 1:
            return f"{month} {to_persian_digits(self.jy)}"

        ny, nm = add_jalali_months(self.jy, self.jm, 1)
        return (
            f"{to_persian_digits(self.start_day)} {month} تا "
            f"{to_persian_digits(self.start_day - 1)} {PERSIAN_MONTHS[nm - 1]} "
            f"{to_persian_digits(ny)}"
        )

    def previous(self) -> "Period":
        jy, jm = add_jalali_months(self.jy, self.jm, -1)
        return _period(jy, jm, self.start_day)


def _start_of(jy: int, jm: int, day: int) -> datetime:
    gy, gm, gd = jalali_to_gregorian(jy, jm, day)
    return datetime(gy, gm, gd, tzinfo=TEHRAN)


def _period(jy: int, jm: int, start_day: int) -> Period:
    ny, nm = add_jalali_months(jy, jm, 1)
    return Period(
        start=_start_of(jy, jm, start_day),
        end=_start_of(ny, nm, start_day),
        jy=jy,
        jm=jm,
        start_day=start_day,
    )


def current_period(now: datetime | None = None) -> Period:
    start_day = AccountingSettings.load().period_start_day
    local = (now or timezone.now()).astimezone(TEHRAN)
    jy, jm, jd = gregorian_to_jalali(local.year, local.month, local.day)

    if jd < start_day:
        jy, jm = add_jalali_months(jy, jm, -1)

    return _period(jy, jm, start_day)
