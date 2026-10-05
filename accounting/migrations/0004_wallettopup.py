import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_payment_status_walletentry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WalletTopUp',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount_rial', models.PositiveBigIntegerField(verbose_name='مبلغ (ریال)')),
                ('status', models.CharField(choices=[('pending', 'در انتظار پرداخت'), ('paid', 'پرداخت شده'), ('failed', 'ناموفق'), ('cancelled', 'لغو شده')], default='pending', max_length=20, verbose_name='وضعیت')),
                ('videopol_payment_id', models.CharField(blank=True, db_index=True, max_length=255, verbose_name='شناسه پرداخت ویدوپل')),
                ('payment_url', models.URLField(blank=True, verbose_name='آدرس پرداخت')),
                ('reference_id', models.CharField(blank=True, max_length=255, verbose_name='شناسه مرجع پرداخت')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان پرداخت')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wallet_top_ups', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'شارژ آنلاین کیف پول',
                'verbose_name_plural': 'شارژهای آنلاین کیف پول',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='top_up',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment', to='accounting.wallettopup', verbose_name='شارژ آنلاین کیف پول'),
        ),
        migrations.AddField(
            model_name='walletentry',
            name='top_up',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wallet_entries', to='accounting.wallettopup', verbose_name='شارژ آنلاین'),
        ),
    ]
