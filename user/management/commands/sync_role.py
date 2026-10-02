from django.contrib.auth.models import (
    Group,
    Permission,
)
from django.core.management.base import (
    BaseCommand,
)
from django.db import transaction


GROUP_PERMISSIONS = {
    "اساتید": [
        # Course
        "course.add_course",
        "course.change_course",
        "course.view_course",

        # Season
        "course.add_courseseason",
        "course.change_courseseason",
        "course.view_courseseason",

        # Session
        "course.add_coursesession",
        "course.change_coursesession",
        "course.view_coursesession",

        # Student progress
        "course.view_coursesessionprogress",

        # Custom
        "course.view_own_course_sales",
        "course.view_own_course_commission",
        "course.view_teacher_sales_ranking",
        "course.view_own_courses",
    ],

    "دانشجویان": [
        "course.view_course",
        "course.view_courseseason",
        "course.view_coursesession",
        "course.view_coursesessionprogress",
    ],

    "فروشنده ها": [
        # Needed to choose products
        "course.view_course",

        # Orders
        "order.add_order",
        "order.change_order",
        "order.delete_order",
        "order.view_order",

        # Requested products
        "order.add_requestedproduct",
        "order.change_requestedproduct",
        "order.delete_requestedproduct",
        "order.view_requestedproduct",

        # Custom sales permissions
        "order.view_own_sales_report",
        "order.view_own_sales_commission",
    ],

    "مدیریت": [
        # Users
        "user.add_user",
        "user.change_user",
        "user.view_user",

        # Courses
        "course.add_course",
        "course.change_course",
        "course.view_course",
        "course.publish_course",

        "course.add_courseseason",
        "course.change_courseseason",
        "course.view_courseseason",

        "course.add_coursesession",
        "course.change_coursesession",
        "course.view_coursesession",

        "course.view_all_courses",
        "course.change_any_course",
        "course.view_all_courses",
        "course.change_any_course",
        "order.view_all_orders",
        "order.change_any_order",

        # Orders
        "order.add_order",
        "order.change_order",
        "order.view_order",
        "order.view_requestedproduct",

        # Reports available in current models
        "course.view_coursesessionprogress",
    ],

    "کارمند اداری": [
        "user.view_user",
        "user.view_studentmentorassignment",

        "course.view_course",
        "course.view_coursesession",
        "course.view_coursesessionprogress",
    ],

    "کارمند حسابداری": [
        # Orders
        "order.view_order",
        "order.view_requestedproduct",

        # Approval
        "order.approve_order",
        "order.reject_order",

        # Accounting
        "accounting.view_bankaccount",
        "accounting.view_payment",
        "accounting.add_payment",
        "accounting.change_payment",
        "order.view_all_orders",
        "order.approve_order",
        "order.reject_order",
    ],

    # مدل‌های call/import هنوز ساخته نشده‌اند.
    "اپراتور تماس": [],

    # پایین‌تر special-case می‌شود.
    "مدیر اصلی": [],
}


def get_permission(
    permission_name: str,
) -> Permission:
    app_label, codename = (
        permission_name.split(".", 1)
    )

    return Permission.objects.get(
        content_type__app_label=app_label,
        codename=codename,
    )


class Command(BaseCommand):
    help = (
        "Create application groups and "
        "synchronize their default permissions."
    )

    @transaction.atomic
    def handle(self, *args, **options):

        for (
            group_name,
            permission_names,
        ) in GROUP_PERMISSIONS.items():

            group, _ = (
                Group.objects.get_or_create(
                    name=group_name,
                )
            )

            if group_name == "مدیر اصلی":
                permissions = (
                    Permission.objects.all()
                )
            else:
                permissions = [
                    get_permission(name)
                    for name
                    in permission_names
                ]

            group.permissions.set(
                permissions
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{group_name}: "
                    f"{len(permissions)} "
                    "permissions synced."
                )
            )