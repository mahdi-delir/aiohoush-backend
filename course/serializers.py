from rest_framework import serializers

from course.models import Course


class CourseSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Course

        fields = [
            "id",
            "teacher",
            "requirements",
            "categories",
            "title",
            "description",
            "level",
            "slug",
            "order",
            "is_published",
            "published_at",
            "can_sale",
            "price",
            "poster",
            "intro_video",
        ]

        read_only_fields = [
            "id",
            "is_published",
            "published_at",
        ]