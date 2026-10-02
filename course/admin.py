from django.contrib import admin

from course.models import (
    Course,
    CourseCategory,
    CourseSeason,
    CourseSession,
    CourseSessionProgress,
    CourseSessionWatch,
    CourseSessionWatchEvent,
    CourseSessionWatchedRange,
)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "slug",
        "order",
        "created_at",
    )

    search_fields = (
        "title",
        "slug",
    )

    ordering = (
        "order",
        "id",
    )


class CourseSeasonInline(admin.TabularInline):
    model = CourseSeason
    extra = 0

    fields = (
        "title",
        "order",
    )

    ordering = (
        "order",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "teacher",
        "level",
        "price",
        "is_published",
        "can_sale",
        "order",
    )

    list_filter = (
        "level",
        "is_published",
        "can_sale",
        "categories",
    )

    search_fields = (
        "title",
        "slug",
        "teacher__mobile",
    )

    list_select_related = (
        "teacher",
    )

    filter_horizontal = (
        "requirements",
        "categories",
    )

    ordering = (
        "order",
        "id",
    )

    inlines = (
        CourseSeasonInline,
    )


class CourseSessionInline(admin.TabularInline):
    model = CourseSession
    extra = 0

    fields = (
        "title",
        "order",
        "duration",
        "is_public",
        "has_homework",
    )

    ordering = (
        "order",
    )


@admin.register(CourseSeason)
class CourseSeasonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "course",
        "order",
        "created_at",
    )

    list_filter = (
        "course",
    )

    search_fields = (
        "title",
        "course__title",
    )

    list_select_related = (
        "course",
    )

    ordering = (
        "course",
        "order",
    )

    inlines = (
        CourseSessionInline,
    )


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "get_course",
        "season",
        "order",
        "duration",
        "is_public",
        "has_homework",
    )

    list_filter = (
        "season__course",
        "season",
        "is_public",
        "has_homework",
    )

    search_fields = (
        "title",
        "season__title",
        "season__course__title",
    )

    list_select_related = (
        "season",
        "season__course",
    )

    ordering = (
        "season__course",
        "season",
        "order",
    )

    @admin.display(
        description="دوره",
        ordering="season__course__title",
    )
    def get_course(self, obj):
        return obj.season.course


@admin.register(CourseSessionProgress)
class CourseSessionProgressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "get_course",
        "session",
        "last_position_ms",
        "unique_watched_ms",
        "total_watched_ms",
        "watch_count",
        "play_count",
        "completed_at",
        "last_watched_at",
    )

    list_filter = (
        "completed_at",
        "session__season__course",
    )

    search_fields = (
        "user__mobile",
        "session__title",
        "session__season__course__title",
    )

    list_select_related = (
        "user",
        "session",
        "session__season",
        "session__season__course",
    )

    @admin.display(
        description="دوره",
        ordering="session__season__course__title",
    )
    def get_course(self, obj):
        return obj.session.season.course


class CourseSessionWatchEventInline(admin.TabularInline):
    model = CourseSessionWatchEvent
    extra = 0

    fields = (
        "sequence",
        "event_type",
        "position_ms",
        "from_position_ms",
        "to_position_ms",
        "playback_rate",
        "client_occurred_at",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "sequence",
    )


@admin.register(CourseSessionWatch)
class CourseSessionWatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "progress",
        "auth_session",
        "start_position_ms",
        "last_position_ms",
        "max_position_ms",
        "watched_ms",
        "started_at",
        "ended_at",
        "end_reason",
    )

    list_filter = (
        "end_reason",
        "started_at",
    )

    list_select_related = (
        "progress",
        "progress__user",
        "progress__session",
        "auth_session",
    )

    date_hierarchy = "started_at"

    inlines = (
        CourseSessionWatchEventInline,
    )


@admin.register(CourseSessionWatchEvent)
class CourseSessionWatchEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "watch",
        "sequence",
        "event_type",
        "position_ms",
        "playback_rate",
        "created_at",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "client_event_id",
    )

    list_select_related = (
        "watch",
    )

    ordering = (
        "-created_at",
    )


@admin.register(CourseSessionWatchedRange)
class CourseSessionWatchedRangeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "progress",
        "start_ms",
        "end_ms",
        "created_at",
    )

    list_select_related = (
        "progress",
        "progress__user",
        "progress__session",
    )

    ordering = (
        "progress",
        "start_ms",
    )