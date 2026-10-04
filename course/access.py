"""قوانین دسترسی کاربر به محتوای دوره (ویدئو، سورس کد).

همهٔ viewها و serializerها باید از همین ماژول استفاده کنند تا قانون
دسترسی فقط در یک جا تعریف شده باشد.
"""

from django.db.models import Exists, OuterRef

from order.models import Order, RequestedProduct


STAFF_VIEW_PERMISSION = "course.view_all_courses"


def approved_purchase_subquery(user):
    """سفارش تأییدشدهٔ کاربر برای دوره‌ای که pk آن از OuterRef می‌آید."""
    return RequestedProduct.objects.filter(
        course_id=OuterRef("pk"),
        order__student=user,
        order__status=Order.STATUS.APPROVED,
        order__is_deleted=False,
    )


def annotate_has_purchased(queryset, user):
    return queryset.annotate(
        has_purchased=Exists(approved_purchase_subquery(user)),
    )


def has_purchased_course(user, course) -> bool:
    return RequestedProduct.objects.filter(
        course=course,
        order__student=user,
        order__status=Order.STATUS.APPROVED,
        order__is_deleted=False,
    ).exists()


def can_access_course(user, course, *, has_purchased=None) -> bool:
    """آیا کاربر به همهٔ جلسات این دوره دسترسی دارد؟

    دسترسی کامل: خرید تأییدشده، مدرس همان دوره، یا مجوز مشاهدهٔ
    همهٔ دوره‌ها (مدیریت). superuser فعال همهٔ مجوزها را دارد.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if course.teacher_id == user.pk:
        return True

    if user.has_perm(STAFF_VIEW_PERMISSION):
        return True

    if has_purchased is None:
        has_purchased = has_purchased_course(user, course)

    return bool(has_purchased)


def can_access_session(user, session, *, course_access=None) -> bool:
    """جلسهٔ عمومی برای همه باز است؛ بقیه فقط با دسترسی به دوره."""
    if session.is_public:
        return True

    if course_access is None:
        course_access = can_access_course(user, session.season.course)

    return bool(course_access)
