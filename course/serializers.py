from rest_framework import serializers

from course.models import Course

from course.models import Course, CourseCategory
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


class CourseCatalogCategorySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = CourseCategory

        fields = [
            "id",
            "title",
            "slug",
        ]


class CourseCatalogSerializer(
    serializers.ModelSerializer
):
    cover = serializers.ImageField(
        source="poster",
        read_only=True,
    )

    duration = serializers.SerializerMethodField()

    episod_count = serializers.IntegerField(
        source="all_sessions",
        read_only=True,
    )

    season_count = serializers.IntegerField(
        read_only=True,
    )

    has_access = serializers.BooleanField(
        read_only=True,
    )

    watched_percent = (
        serializers.SerializerMethodField()
    )

    categories = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Course

        fields = [
            "id",
            "title",
            "description",
            "cover",
            "duration",
            "episod_count",
            "season_count",
            "level",
            "has_access",
            "slug",
            "categories",
            "watched_percent",
            "price",
            "can_sale",
        ]

    def get_duration(
        self,
        obj,
    ):
        duration = obj.total_duration

        if not duration:
            return "0 دقیقه"

        seconds = int(
            duration.total_seconds()
        )

        hours = seconds // 3600
        minutes = (
            seconds % 3600
        ) // 60

        if hours and minutes:
            return (
                f"{hours} ساعت و "
                f"{minutes} دقیقه"
            )

        if hours:
            return f"{hours} ساعت"

        return f"{minutes} دقیقه"

    def get_watched_percent(
        self,
        obj,
    ):
        if not obj.all_sessions:
            return 0

        return round(
            (
                obj.completed_sessions
                / obj.all_sessions
            )
            * 100
        )

    def get_categories(
        self,
        obj,
    ):
        return [
            {
                "en": category.slug,
                "fa": category.title,
            }
            for category
            in obj.categories.all()
        ]