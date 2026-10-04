import course.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursesession',
            name='source_code',
            field=models.FileField(blank=True, null=True, storage=course.models.private_media_storage, upload_to=course.models.session_source_code_upload_to, verbose_name='سورس کد های جلسه'),
        ),
    ]
