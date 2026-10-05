"""رتبه‌بندی ماهانهٔ منتورها بر اساس فروش.

هر ۱۰ میلیون تومان فروش = ۱۵٬۰۰۰ امتیاز (تناسبی). فقط امتیاز نمایش
داده می‌شود، نه مبلغ.
"""

from django.db.models import Avg, Count, Q, Sum

from accounting.models import SalesCredit
from accounting.services.periods import Period, current_period
from user.models import MentorReview, User
from user.services.mentor import full_name


POINTS_PER_UNIT = 15_000
UNIT_RIAL = 10_000_000 * 10  # ده میلیون تومان

TOP_COUNT = 10


def sales_to_points(amount_rial: int) -> int:
    return max(0, amount_rial) * POINTS_PER_UNIT // UNIT_RIAL


def rank_period(period: Period) -> list[tuple[int, int]]:
    """[(seller_id, points)] به ترتیب رتبه؛ فقط کسانی که فروش مثبت دارند."""
    totals = (
        SalesCredit.objects
        .filter(created_at__gte=period.start, created_at__lt=period.end)
        .values("seller_id")
        .annotate(total=Sum("amount"))
        .filter(total__gt=0)
    )

    ranked = [
        (row["seller_id"], sales_to_points(row["total"]))
        for row in totals
    ]
    # امتیاز برابر: کسی که زودتر ثبت‌نام کرده جلوتر (پایدار و قابل پیش‌بینی)
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def build_leaderboard(request) -> dict:
    from django.utils import timezone

    from user.services.mentor import avatar_url

    period = current_period()
    current = rank_period(period)[:TOP_COUNT]
    previous_ranks = {
        seller_id: index + 1
        for index, (seller_id, _) in enumerate(rank_period(period.previous()))
    }

    seller_ids = [seller_id for seller_id, _ in current]

    users = {
        user.pk: user
        for user in User.objects.filter(pk__in=seller_ids)
    }

    review_stats = {
        row["mentor_id"]: row
        for row in (
            MentorReview.objects
            .filter(mentor_id__in=seller_ids, is_published=True)
            .values("mentor_id")
            .annotate(average=Avg("rating"), count=Count("id"))
        )
    }

    mentors = []
    for index, (seller_id, points) in enumerate(current):
        user = users[seller_id]
        stats = review_stats.get(seller_id)

        mentors.append({
            "id": seller_id,
            "rank": index + 1,
            "previousRank": previous_ranks.get(seller_id),
            "name": full_name(user),
            # فیلد تخصص هنوز در مدل نیست.
            "specialty": "",
            "bio": user.bio or "",
            "avatarUrl": avatar_url(user, request),
            "points": points,
            "rating": round(float(stats["average"]), 2) if stats else None,
            "reviewCount": stats["count"] if stats else 0,
        })

    return {
        "periodLabel": period.label,
        "comparisonLabel": "نسبت به دورهٔ قبل",
        "updatedAt": timezone.now().isoformat(),
        "rankingDescription": (
            "رتبه‌بندی بر اساس امتیاز فروش منتورها در دورهٔ جاری است و "
            "ابتدای هر دوره از صفر شروع می‌شود."
        ),
        "mentors": mentors,
    }
