from order.models import Order, RequestedProduct

from course.models import Course


LEVEL_RANK = {
    Course.LEVEL.BEGINNER: 0,
    Course.LEVEL.INTERMEDIATE: 1,
    Course.LEVEL.ADVANCED: 2,
}


def purchased_course_ids(user) -> set[int]:
    return set(
        RequestedProduct.objects
        .filter(
            order__student=user,
            order__status=Order.STATUS.APPROVED,
            order__is_deleted=False,
            course__isnull=False,
        )
        .values_list("course_id", flat=True)
    )


def recommend_course(user) -> Course | None:
    purchased = purchased_course_ids(user)

    candidates = (
        Course.objects
        .filter(is_published=True, can_sale=True)
        .exclude(pk__in=purchased)
        .exclude(teacher=user)
        .prefetch_related("requirements", "categories")
        .order_by("order", "id")
    )

    owned_categories = set(
        Course.categories.through.objects
        .filter(course_id__in=purchased)
        .values_list("coursecategory_id", flat=True)
    )

    ranked = []

    for course in candidates:
        requirements = {item.pk for item in course.requirements.all()}

        if not requirements <= purchased:
            continue

        if not purchased and (
            requirements or course.level != Course.LEVEL.BEGINNER
        ):
            continue

        if requirements & purchased:
            group = 0
        elif {item.pk for item in course.categories.all()} & owned_categories:
            group = 1
        else:
            group = 2

        ranked.append((
            group,
            LEVEL_RANK.get(course.level, len(LEVEL_RANK)),
            course.order,
            course.pk,
            course,
        ))

    if not ranked:
        return None

    return min(ranked, key=lambda item: item[:4])[-1]
