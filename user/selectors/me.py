from typing import Any

from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
)

from course.models import Course
from course.services.gift_watch import has_watched_all_gifts
from order.models import Order, RequestedProduct
from user.models import User


def get_user_data(
    *,
    user: User,
) -> dict[str, Any]:

    approved_product = RequestedProduct.objects.filter(
        course_id=OuterRef("pk"),
        order__student=user,
        order__status=Order.STATUS.APPROVED,
        order__is_deleted=False,
    )

    courses = (
        Course.objects
        .annotate(
            user_has_access=Exists(
                approved_product,
            ),
        )
        .filter(
            user_has_access=True,
        )
        .annotate(
            all_sessions=Count(
                "seasons__sessions",
                distinct=True,
            ),

            completed_sessions=Count(
                "seasons__sessions",
                filter=Q(
                    seasons__sessions__user_progresses__user=user,
                    seasons__sessions__user_progresses__completed_at__isnull=False,
                ),
                distinct=True,
            ),
        )
        .order_by(
            "order",
            "id",
        )
    )

    active_courses: list[dict[str, Any]] = []

    for course in courses:
        all_sessions = course.all_sessions
        completed_sessions = course.completed_sessions

        # دورهٔ تمام‌شده «فعال» حساب نمی‌شود.
        if all_sessions and completed_sessions >= all_sessions:
            continue

        completed_percent = (
            completed_sessions
            / all_sessions
            * 100
            if all_sessions
            else 0
        )

        active_courses.append(
            {
                "id": course.pk,
                "title": course.title,
                "slug": course.slug,

                "all_sessions": all_sessions,

                "current_session":
                    completed_sessions,

                # فعلاً spelling قرارداد frontend
                # خودت را حفظ می‌کنیم.
                "completed_percent": round(
                    completed_percent,
                    2,
                ),
            }
        )

    return {
        # همهٔ ویدئوهای هدیهٔ فعال را تا ۹۰٪ دیده باشد.
        "watched_gift": has_watched_all_gifts(user),

        # دورهٔ نیمه‌تمام دارد؛ active_courses به ترتیب نمایش دوره‌هاست.
        "has_course": bool(
            active_courses,
        ),

        "active_courses":
            active_courses,
    }