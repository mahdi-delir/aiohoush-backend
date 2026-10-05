from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse

from rest_framework import serializers

from aiohoush.utilities.uploads import validate_homework_attachment


from course.models import (
    Course,
    CourseCategory,
    CourseSeason,
    CourseSession,
    CourseSessionHomeworkSubmission,
    CourseSessionWatch,
    CourseSessionWatchEvent,
    GiftVideo,
)
from course.services.watch import progress_percent, session_duration_ms
def format_duration(value):
    if not value:
        return "0 دقیقه"

    seconds = int(value.total_seconds())

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours and minutes:
        return f"{hours} ساعت و {minutes} دقیقه"

    if hours:
        return f"{hours} ساعت"

    return f"{minutes} دقیقه"


class CourseSessionDetailSerializer(
    serializers.ModelSerializer
):
    """جلسه در صفحهٔ دوره.

    برای جلسهٔ قفل (کاربر بدون دسترسی و جلسهٔ غیرعمومی) آدرس ویدئو و
    سورس کد هرگز ارسال نمی‌شود. مقدار ``can_access_course`` باید توسط
    view در context قرار بگیرد؛ پیش‌فرض بسته است.
    """

    playerUrl = serializers.SerializerMethodField()

    cover = serializers.ImageField(
        source="poster",
        allow_null=True,
        read_only=True,
    )

    is_locked = serializers.SerializerMethodField()

    watched_percent = serializers.SerializerMethodField()

    has_source_code = serializers.SerializerMethodField()

    source_code_url = serializers.SerializerMethodField()

    duration = serializers.SerializerMethodField()

    class Meta:
        model = CourseSession

        fields = [
            "id",
            "title",
            "description",
            "order",
            "duration",
            "playerUrl",
            "cover",
            "is_locked",
            "watched_percent",
            "has_source_code",
            "source_code_url",
            "has_homework",
            "is_public",
        ]

    def _is_locked(self, obj):
        course_access = self.context.get(
            "can_access_course",
            False,
        )
        return not (obj.is_public or course_access)

    def get_is_locked(self, obj):
        return self._is_locked(obj)

    def get_watched_percent(self, obj):
        progress = self.context.get(
            "progress_by_session",
            {},
        ).get(obj.pk)

        return progress_percent(
            progress,
            session_duration_ms(obj),
        )

    def get_playerUrl(self, obj):
        if self._is_locked(obj):
            return None
        return obj.video_url or None

    def get_has_source_code(self, obj):
        return bool(obj.source_code)

    def get_source_code_url(self, obj):
        # فایل در storage خصوصی است؛ فقط آدرس endpoint محافظت‌شده
        # برگردانده می‌شود، نه آدرس مستقیم فایل.
        if not obj.source_code or self._is_locked(obj):
            return None
        return reverse(
            "session-source-code",
            kwargs={"session_id": obj.pk},
        )

    def get_duration(self, obj):
        return format_duration(obj.duration)


class CourseSeasonDetailSerializer(
    serializers.ModelSerializer
):
    subject = serializers.CharField(
        source="description",
        allow_blank=True,
        allow_null=True,
        read_only=True,
    )

    duration = serializers.SerializerMethodField()

    episod_count = serializers.IntegerField(
        source="sessions.count",
        read_only=True,
    )

    episods = CourseSessionDetailSerializer(
        source="sessions",
        many=True,
        read_only=True,
    )

    class Meta:
        model = CourseSeason

        fields = [
            "id",
            "title",
            "subject",
            "order",
            "duration",
            "episod_count",
            "episods",
        ]

    def get_duration(self, obj):
        total = None

        for session in obj.sessions.all():
            if session.duration:
                total = (
                    session.duration
                    if total is None
                    else total + session.duration
                )

        return format_duration(total)


class CourseDetailInfoSerializer(
    serializers.ModelSerializer
):
    short_description = serializers.CharField(
        source="description",
        allow_blank=True,
        allow_null=True,
        read_only=True,
    )

    cover = serializers.ImageField(
        source="poster",
        allow_null=True,
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

    watched_percent = serializers.IntegerField(
        read_only=True,
    )

    categories = serializers.SerializerMethodField()

    class Meta:
        model = Course

        fields = [
            "id",
            "title",
            "short_description",
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
            "intro_video",
        ]

    def get_duration(self, obj):
        return format_duration(obj.total_duration)

    def get_categories(self, obj):
        return [
            {
                "en": category.slug,
                "fa": category.title,
            }
            for category in obj.categories.all()
        ]

class CourseDetailSerializer(
    serializers.ModelSerializer
):
    course = serializers.SerializerMethodField()

    seasons = CourseSeasonDetailSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Course
        fields = [
            "course",
            "seasons",
        ]

    def get_course(self, obj):
        return CourseDetailInfoSerializer(
            obj,
            context=self.context,
        ).data

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

class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = (
            CourseSessionHomeworkSubmission
        )

        fields = [
            "id",
            "session",
            "answer",
            "attachment",
            "status",
            "feedback",
            "submitted_at",
            "updated_at",
            "reviewed_at",
        ]

        read_only_fields = [
            "id",
            "session",
            "status",
            "feedback",
            "submitted_at",
            "updated_at",
            "reviewed_at",
        ]

    def validate_attachment(self, value):
        if value:
            try:
                validate_homework_attachment(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        answer = attrs.get(
            "answer",
            "",
        )

        attachment = attrs.get(
            "attachment",
        )

        if (
            not answer.strip()
            and not attachment
        ):
            raise serializers.ValidationError(
                "متن تمرین یا فایل تمرین "
                "باید ارسال شود."
            )

        return attrs

class GiftVideoSerializer(
    serializers.ModelSerializer
):
    playerUrl = serializers.CharField(
        source="player_url",
        allow_blank=True,
        allow_null=True,
        read_only=True,
    )

    duration = serializers.SerializerMethodField()

    class Meta:
        model = GiftVideo

        fields = [
            "id",
            "title",
            "slug",
            "duration",
            "playerUrl",
            "cover",
            "order",
            "is_public",
        ]

    def get_duration(self, obj):
        return format_duration(obj.duration)

MAX_POSITION_MS = 24 * 60 * 60 * 1000


class WatchEventInputSerializer(serializers.Serializer):
    client_event_id = serializers.UUIDField()
    sequence = serializers.IntegerField(min_value=0, max_value=1_000_000)
    event_type = serializers.ChoiceField(
        choices=CourseSessionWatchEvent.EVENT.choices,
    )
    position_ms = serializers.IntegerField(min_value=0, max_value=MAX_POSITION_MS)
    from_position_ms = serializers.IntegerField(
        min_value=0, max_value=MAX_POSITION_MS, required=False, allow_null=True,
    )
    to_position_ms = serializers.IntegerField(
        min_value=0, max_value=MAX_POSITION_MS, required=False, allow_null=True,
    )
    playback_rate = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=0, max_value=16,
        required=False, allow_null=True,
    )
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)


class WatchBatchInputSerializer(serializers.Serializer):
    events = WatchEventInputSerializer(many=True, max_length=200)
    ranges = serializers.ListField(
        child=serializers.ListField(
            child=serializers.IntegerField(min_value=0, max_value=MAX_POSITION_MS),
            min_length=2,
            max_length=2,
        ),
        max_length=500,
        required=False,
        default=list,
    )
    position_ms = serializers.IntegerField(min_value=0, max_value=MAX_POSITION_MS)
    duration_ms = serializers.IntegerField(
        min_value=0, max_value=MAX_POSITION_MS, required=False, allow_null=True,
    )
    end_reason = serializers.ChoiceField(
        choices=CourseSessionWatch.ENDREASON.choices,
        required=False,
        allow_null=True,
    )

    def validate_events(self, value):
        if not value:
            raise serializers.ValidationError("حداقل یک رویداد لازم است.")
        return value

    def validate_ranges(self, value):
        return [
            (start, end)
            for start, end in value
            if end > start
        ]
