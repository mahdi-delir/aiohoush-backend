import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_persian_verbose_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='max_devices',
            field=models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)], verbose_name='حداکثر دستگاه‌های همزمان'),
        ),
    ]
