from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_accountingsettings_salescredit'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bankaccount',
            options={'verbose_name': 'حساب بانکی', 'verbose_name_plural': 'حساب\u200cهای بانکی'},
        ),
    ]
