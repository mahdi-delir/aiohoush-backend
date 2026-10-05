from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0003_private_session_source_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursecategory',
            name='icon',
            field=models.CharField(choices=[('school', 'مدرسه (پیش‌فرض)'), ('web', 'وب'), ('code', 'کد'), ('chatbot', 'هوش مصنوعی'), ('drawing', 'طراحی'), ('microphone', 'میکروفون'), ('book', 'کتاب'), ('calculator', 'ماشین‌حساب'), ('google', 'گوگل'), ('resume', 'رزومه'), ('training', 'آموزش')], default='school', max_length=20, verbose_name='آیکون'),
        ),
    ]
