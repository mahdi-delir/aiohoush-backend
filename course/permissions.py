from rest_framework.permissions import (
    BasePermission,
)


class CourseManagementPermission(
    BasePermission
):
    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        action = view.action

        if action in {
            "list",
            "retrieve",
        }:
            return (
                user.has_perm(
                    "course.view_all_courses"
                )
                or
                user.has_perm(
                    "course.view_own_courses"
                )
            )

        if action == "create":
            return user.has_perm(
                "course.add_course"
            )

        if action in {
            "update",
            "partial_update",
        }:
            return user.has_perm(
                "course.change_course"
            )

        if action == "publish":
            return user.has_perm(
                "course.publish_course"
            )

        return False

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user
        action = view.action

        if action in {
            "list",
            "retrieve",
        }:
            if user.has_perm(
                "course.view_all_courses"
            ):
                return True

            return (
                user.has_perm(
                    "course.view_own_courses"
                )
                and
                obj.teacher_id == user.id
            )

        if action in {
            "update",
            "partial_update",
        }:
            if user.has_perm(
                "course.change_any_course"
            ):
                return True

            return (
                user.has_perm(
                    "course.change_course"
                )
                and
                obj.teacher_id == user.id
            )

        if action == "publish":
            if not user.has_perm(
                "course.publish_course"
            ):
                return False

            if user.has_perm(
                "course.change_any_course"
            ):
                return True

            return (
                obj.teacher_id == user.id
            )
        
        

        return False