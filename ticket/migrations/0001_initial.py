import course.models
import django.db.models.deletion
import ticket.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('course', '0004_coursecategory_icon'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(choices=[('mentor', 'منتور'), ('teacher', 'استاد'), ('finance', 'واحد مالی'), ('management', 'مدیریت')], max_length=20, verbose_name='بخش')),
                ('subject', models.CharField(max_length=150, verbose_name='موضوع')),
                ('status', models.CharField(choices=[('waiting', 'در انتظار پاسخ'), ('answered', 'پاسخ داده شده'), ('closed', 'بسته شده')], default='waiting', max_length=10, verbose_name='وضعیت')),
                ('last_message_at', models.DateTimeField(db_index=True, verbose_name='آخرین پیام')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان بسته شدن')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='آخرین تغییر')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='assigned_tickets', to=settings.AUTH_USER_MODEL, verbose_name='گیرنده')),
                ('closed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='closed_tickets', to=settings.AUTH_USER_MODEL, verbose_name='بسته شده توسط (خالی = خودکار)')),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to='course.course', verbose_name='دوره (تیکت استاد)')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to=settings.AUTH_USER_MODEL, verbose_name='دانشجو')),
            ],
            options={
                'verbose_name': 'تیکت',
                'verbose_name_plural': 'تیکت‌ها',
                'ordering': ('-last_message_at',),
                'indexes': [
                    models.Index(fields=['student', '-last_message_at'], name='ticket_student_idx'),
                    models.Index(fields=['department', 'status'], name='ticket_department_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(models.Q(('department', 'teacher'), _negated=True), ('course__isnull', False), _connector='OR'), name='teacher_ticket_has_course'),
                ],
            },
        ),
        migrations.CreateModel(
            name='TicketMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True, verbose_name='متن')),
                ('attachment', models.FileField(blank=True, null=True, storage=course.models.private_media_storage, upload_to=ticket.models.ticket_file_upload_to, verbose_name='پیوست')),
                ('attachment_name', models.CharField(blank=True, max_length=255, verbose_name='نام اصلی پیوست')),
                ('voice', models.FileField(blank=True, null=True, storage=course.models.private_media_storage, upload_to=ticket.models.ticket_file_upload_to, verbose_name='پیام صوتی')),
                ('voice_duration_ms', models.PositiveIntegerField(blank=True, null=True, verbose_name='مدت پیام صوتی (میلی‌ثانیه)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ticket_messages', to=settings.AUTH_USER_MODEL, verbose_name='نویسنده')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='ticket.ticket', verbose_name='تیکت')),
            ],
            options={
                'verbose_name': 'پیام تیکت',
                'verbose_name_plural': 'پیام‌های تیکت',
                'ordering': ('created_at', 'id'),
            },
        ),
    ]
