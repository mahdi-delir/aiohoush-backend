import aiohoush.utilities.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='telegram_id',
            field=models.CharField(blank=True, help_text='بدون @؛ مثلاً aiohoush', max_length=32, null=True, validators=[aiohoush.utilities.validators.telegram_id_validator], verbose_name='آی‌دی تلگرام'),
        ),
        migrations.CreateModel(
            name='MentorReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(verbose_name='امتیاز')),
                ('text', models.TextField(blank=True, max_length=1000, verbose_name='متن نظر')),
                ('is_published', models.BooleanField(default=True, verbose_name='منتشر شده')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='آخرین تغییر')),
                ('mentor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mentor_reviews_received', to=settings.AUTH_USER_MODEL, verbose_name='منتور')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mentor_reviews_written', to=settings.AUTH_USER_MODEL, verbose_name='دانشجو')),
            ],
            options={
                'verbose_name': 'نظر دربارهٔ منتور',
                'verbose_name_plural': 'نظرهای دربارهٔ منتور',
                'ordering': ('-created_at',),
                'constraints': [
                    models.UniqueConstraint(fields=('mentor', 'student'), name='unique_review_per_student_mentor'),
                    models.CheckConstraint(condition=models.Q(('rating__gte', 1), ('rating__lte', 5)), name='mentor_review_rating_1_5'),
                ],
            },
        ),
        migrations.CreateModel(
            name='MentorRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('open', 'در انتظار'), ('done', 'رسیدگی شده')], default='open', max_length=10, verbose_name='وضعیت')),
                ('handled_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان رسیدگی')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان درخواست')),
                ('handled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handled_mentor_requests', to=settings.AUTH_USER_MODEL, verbose_name='رسیدگی کننده')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentor_requests', to=settings.AUTH_USER_MODEL, verbose_name='دانشجو')),
            ],
            options={
                'verbose_name': 'درخواست منتور',
                'verbose_name_plural': 'درخواست‌های منتور',
                'ordering': ('-created_at',),
                'constraints': [models.UniqueConstraint(condition=models.Q(('status', 'open')), fields=('student',), name='unique_open_mentor_request')],
            },
        ),
    ]
