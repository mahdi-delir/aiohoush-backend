from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0002_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='smsserverresponse',
            options={'verbose_name': 'گزارش ارسال پیامک', 'verbose_name_plural': 'گزارش\u200cهای ارسال پیامک'},
        ),
        migrations.AlterModelOptions(
            name='otpsmstoken',
            options={'verbose_name': 'کد یکبار مصرف', 'verbose_name_plural': 'کدهای یکبار مصرف'},
        ),
    ]
