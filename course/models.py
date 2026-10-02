import uuid
from django.db import models
from django.conf import settings

# Create your models here.

class CourseCategory(models.Model):
    title = models.CharField(
        verbose_name='دسته بندی',
        max_length=20
    )
    description = models.TextField(
        verbose_name= 'توضیحات',
        blank = True,
        null = True
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='اسلاگ'
    )
    order = models.PositiveIntegerField(
        verbose_name='ترتیب',
        default = 1
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name = 'زمان ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='زمان به روزرسانی'
    )

class Course(models.Model):
    class LEVEL(models.TextChoices):
        BEGINNER = 'beginner', 'مبتدی'
        INTERMEDIATE = 'intermediate', 'متوسط'
        ADVANCED = 'advanced', 'پیشرفته'

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='مدرس',
        related_name='teached_courses',
        on_delete=models.PROTECT
    )

    requirements = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name="required_by_courses",
        verbose_name="پیش‌نیازها",
    )

    categories = models.ManyToManyField(
        'course.CourseCategory',
        verbose_name="دسته‌بندی‌ها",
        related_name="courses",    
    )

    title = models.CharField(
        max_length=100,
        verbose_name='عنوان'
    )

    description = models.TextField(
        verbose_name='توضیحات دوره',
        blank = True,
        null=True
    )

    level = models.CharField(
        max_length=15,
        verbose_name='سطح دوره',
        choices=LEVEL.choices
    )

    slug = models.SlugField(
        verbose_name='اسلاگ',
        unique=True
    )

    order = models.PositiveIntegerField(
        verbose_name = 'ترتیب نمایش',
        default = 1
    )

    is_published = models.BooleanField(
        verbose_name = 'وضعیت انتشار',
        default = True
    )

    published_at = models.DateTimeField(
        verbose_name='زمان انتشار دوره',
        blank = True,
        null = True
    )

    can_sale = models.BooleanField(
        verbose_name = 'قابل فروش؟',
        default = True
    )

    price = models.DecimalField(
        verbose_name = '(ریال)قیمت دوره',
        max_digits=10,
        decimal_places=0
    )

    poster = models.ImageField(
        verbose_name='عکس شاخص',
        blank = True,
        null=True,
        upload_to='course-posters/'
    )

    intro_video = models.CharField(
        max_length=255,
        verbose_name = 'ویدئو معرفی',
        blank = True,
        null = True,
    )

    created_at = models.DateTimeField(
        verbose_name='زمان ایجاد',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        verbose_name = 'آخرین تغییر',
        auto_now=True
    )

    def __str__(self):
        return self.title
    class Meta:
        permissions = [
            (
                "publish_course",
                "Can publish course",
            ),
            (
                "view_own_course_sales",
                "Can view own course sales",
            ),
            (
                "view_own_course_commission",
                "Can view own course commission",
            ),
            (
                "view_teacher_sales_ranking",
                "Can view teacher sales ranking",
            ),
        ]

class CourseSeason(models.Model):
    title = models.CharField(
        max_length=50,
        verbose_name='عنوان فصل'
    )
    description = models.TextField(
        verbose_name='توضیحات فصل',
        blank=True,
        null=True
    )
    course = models.ForeignKey(
        'course.Course',
        verbose_name='دوره',
        on_delete=models.CASCADE,
        related_name='seasons'
    )
    order = models.PositiveIntegerField(
        verbose_name='ترتیب فصل',
        default=1
    )
    created_at = models.DateTimeField(
        verbose_name='زمان ایجاد',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='آخرین تغییر',
        auto_now=True
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_course_season_order",
            ),
        ]

class CourseSession(models.Model):
    season = models.ForeignKey(
        'course.CourseSeason',
        verbose_name = 'فصل',
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    order = models.PositiveIntegerField(
        verbose_name = 'ترتیب',
        default=1
    )

    title = models.CharField(
        max_length = 25,
        verbose_name = 'عنوان جلسه'
    )

    description = models.CharField(
        max_length = 50,
        verbose_name = 'توضیحات',
        blank = True,
        null = True
    )

    duration = models.DurationField(
        verbose_name = 'مدت زمان',
        blank = True,
        null = True
    )

    video_url = models.CharField(
        max_length = 255,
        verbose_name = 'آدرس ویدئو',
        blank = True,
        null = True
    )

    poster = models.ImageField(
        verbose_name = 'عکس شاخص',
        blank = True,
        null = True,
        upload_to='course-session-posters/'
    )

    source_code = models.FileField(
        upload_to='course-source-codes/',
        blank = True,
        null = True,
        verbose_name = 'سورس کد های جلسه'
    )

    has_homework = models.BooleanField(
        verbose_name = 'جلسه دارای تمرین؟'
    )

    is_public = models.BooleanField(
        default = False,
        verbose_name='جلسه عمومی؟'
    )

    created_at = models.DateTimeField(
        verbose_name='زمان ایجاد',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        verbose_name='آخرین تغییر',
        auto_now=True
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["season", "order"],
                name="unique_season_session_order",
            ),
        ]

class CourseSessionProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_session_progresses",
        verbose_name="کاربر",
    )

    session = models.ForeignKey(
        "course.CourseSession",
        on_delete=models.CASCADE,
        related_name="user_progresses",
        verbose_name="جلسه",
    )

    # آخرین جایی که player کاربر روی آن بوده
    last_position_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="آخرین موقعیت پخش به میلی‌ثانیه",
    )

    # دورترین نقطه‌ای که کاربر در timeline دیده
    max_position_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="بیشترین موقعیت مشاهده‌شده",
    )

    # مجموع واقعی بازه‌های یکتای مشاهده‌شده
    unique_watched_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="زمان مشاهده یکتا",
    )

    # مجموع کل زمان تماشا با احتساب تماشای مجدد
    total_watched_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="کل زمان مشاهده",
    )

    # چند نوبت مستقل وارد تماشای این جلسه شده
    watch_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد دفعات مشاهده",
    )

    # تعداد دفعات واقعی فشردن play
    play_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد دفعات پخش",
    )

    last_watched_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="آخرین مشاهده",
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="زمان تکمیل جلسه",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین تغییر",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "session"],
                name="unique_user_session_progress",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "-last_watched_at"],
                name="course_progress_user_last_idx",
            ),
        ]

class CourseSessionWatch(models.Model):

    class ENDREASON(models.TextChoices):
        ENDED = "ended", "پایان ویدئو"
        NAVIGATION = "navigation", "خروج کاربر"
        INACTIVITY = "inactivity", "عدم فعالیت"
        ERROR = "error", "خطای پخش"
        UNKNOWN = "unknown", "نامشخص"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    progress = models.ForeignKey(
        "course.CourseSessionProgress",
        on_delete=models.CASCADE,
        related_name="watches",
        verbose_name="پیشرفت",
    )

    auth_session = models.ForeignKey(
        "user.AuthSession",
        on_delete=models.SET_NULL,
        related_name="course_watches",
        blank=True,
        null=True,
        verbose_name="نشست کاربر",
    )

    start_position_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="موقعیت شروع",
    )

    last_position_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="آخرین موقعیت",
    )

    max_position_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="بیشترین موقعیت",
    )

    watched_ms = models.PositiveBigIntegerField(
        default=0,
        verbose_name="زمان مشاهده در این نوبت",
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="شروع مشاهده",
    )

    ended_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="پایان مشاهده",
    )

    end_reason = models.CharField(
        max_length=20,
        choices=ENDREASON.choices,
        blank=True,
        verbose_name="دلیل پایان مشاهده",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "progress",
                    "-started_at",
                ],
                name="course_watch_progress_idx",
            ),
        ]

class CourseSessionWatchEvent(models.Model):

    class EVENT(models.TextChoices):
        PLAY = "play", "پخش"
        PAUSE = "pause", "توقف"
        SEEK = "seek", "جابجایی"
        HEARTBEAT = "heartbeat", "ادامه مشاهده"
        ENDED = "ended", "پایان"
        RATE_CHANGE = "rate_change", "تغییر سرعت"
        ERROR = "error", "خطا"

    watch = models.ForeignKey(
        "course.CourseSessionWatch",
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="مشاهده",
    )

    sequence = models.PositiveIntegerField(
        verbose_name="شماره ترتیب رویداد",
    )

    client_event_id = models.UUIDField(
        unique=True,
        verbose_name="شناسه رویداد سمت کلاینت",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT.choices,
        verbose_name="نوع رویداد",
    )

    position_ms = models.PositiveBigIntegerField(
        verbose_name="موقعیت ویدئو",
    )

    # برای seek
    from_position_ms = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name="موقعیت قبل",
    )

    to_position_ms = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name="موقعیت بعد",
    )

    playback_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="سرعت پخش",
    )

    client_occurred_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="زمان رویداد در کلاینت",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان دریافت در سرور",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="اطلاعات تکمیلی",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["watch", "sequence"],
                name="unique_watch_event_sequence",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "watch",
                    "created_at",
                ],
                name="course_watch_event_idx",
            ),
        ]

class CourseSessionWatchedRange(models.Model):
    progress = models.ForeignKey(
        "course.CourseSessionProgress",
        on_delete=models.CASCADE,
        related_name="watched_ranges",
        verbose_name="پیشرفت",
    )

    start_ms = models.PositiveBigIntegerField(
        verbose_name="شروع بازه",
    )

    end_ms = models.PositiveBigIntegerField(
        verbose_name="پایان بازه",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    end_ms__gt=models.F("start_ms")
                ),
                name="watched_range_end_gt_start",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "progress",
                    "start_ms",
                    "end_ms",
                ],
                name="course_watched_range_idx",
            ),
        ]