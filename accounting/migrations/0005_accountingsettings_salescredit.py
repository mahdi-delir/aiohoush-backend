import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_wallettopup'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start_day', models.PositiveSmallIntegerField(default=1, help_text='دورهٔ حسابرسی و رتبه‌بندی منتورها از این روز هر ماه شمسی شروع می‌شود (۱ تا ۲۹).', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(29)], verbose_name='روز شروع دورهٔ ماهانه')),
            ],
            options={
                'verbose_name': 'تنظیمات حسابداری',
                'verbose_name_plural': 'تنظیمات حسابداری',
            },
        ),
        migrations.CreateModel(
            name='SalesCredit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.BigIntegerField(verbose_name='مبلغ (ریال، مرجوعی منفی)')),
                ('kind', models.CharField(choices=[('sale', 'فروش'), ('refund', 'مرجوعی')], max_length=10, verbose_name='نوع')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='زمان ثبت')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sales_credits', to='accounting.payment', verbose_name='پرداخت')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sales_credits', to=settings.AUTH_USER_MODEL, verbose_name='فروشنده')),
            ],
            options={
                'verbose_name': 'فروش فروشنده',
                'verbose_name_plural': 'فروش فروشندگان',
                'ordering': ('-created_at',),
                'constraints': [models.UniqueConstraint(condition=models.Q(('kind', 'sale')), fields=('payment',), name='unique_sale_credit_per_payment')],
            },
        ),
    ]
