from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_telegram_mentor_review_request'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'کاربر', 'verbose_name_plural': 'کاربران'},
        ),
        migrations.AlterModelOptions(
            name='userprofilepicture',
            options={'verbose_name': 'عکس پروفایل', 'verbose_name_plural': 'عکس\u200cهای پروفایل'},
        ),
        migrations.AlterModelOptions(
            name='referralcode',
            options={'verbose_name': 'کد معرف', 'verbose_name_plural': 'کدهای معرف'},
        ),
        migrations.AlterModelOptions(
            name='studentmentorassignment',
            options={'verbose_name': 'تخصیص منتور', 'verbose_name_plural': 'تخصیص\u200cهای منتور'},
        ),
        migrations.AlterModelOptions(
            name='authsession',
            options={'verbose_name': 'نشست ورود', 'verbose_name_plural': 'نشست\u200cهای ورود'},
        ),
    ]
