import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_initial'),
        ('order', '0003_aiproductorder_paid_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='payment',
            options={
                'permissions': [('confirm_payment', 'Can confirm or reject payment')],
                'verbose_name': 'پرداخت',
                'verbose_name_plural': 'پرداخت‌ها',
            },
        ),
        migrations.AlterField(
            model_name='payment',
            name='bank',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='incomes', to='accounting.bankaccount', verbose_name='حساب دریافت کننده'),
        ),
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('pending', 'در انتظار تأیید'), ('confirmed', 'تأیید شده'), ('rejected', 'رد شده')], default='pending', max_length=10, verbose_name='وضعیت'),
        ),
        migrations.AddField(
            model_name='payment',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reviewed_payments', to=settings.AUTH_USER_MODEL, verbose_name='بررسی کننده'),
        ),
        migrations.AddField(
            model_name='payment',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='زمان بررسی'),
        ),
        migrations.AddField(
            model_name='payment',
            name='ai_order',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment', to='order.aiproductorder', verbose_name='سفارش محصول هوش مصنوعی'),
        ),
        migrations.AddField(
            model_name='payment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='زمان ثبت'),
        ),
        migrations.CreateModel(
            name='WalletEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('credit', 'بستانکار (+)'), ('debit', 'بدهکار (−)')], max_length=6, verbose_name='جهت')),
                ('amount', models.PositiveBigIntegerField(verbose_name='مبلغ (ریال)')),
                ('kind', models.CharField(choices=[('deposit', 'واریز'), ('course_purchase', 'خرید دوره'), ('ai_purchase', 'خرید محصول هوش مصنوعی'), ('reversal', 'سند معکوس'), ('charge', 'شارژ از طرف آیوهوش'), ('installment', 'قسط'), ('commission', 'پورسانت'), ('reward', 'تشویق'), ('penalty', 'جریمه'), ('salary', 'حقوق'), ('salary_payout', 'پرداخت حقوق'), ('withdrawal', 'برداشت')], max_length=20, verbose_name='نوع')),
                ('title', models.CharField(max_length=255, verbose_name='عنوان (نمایش به کاربر)')),
                ('description', models.TextField(blank=True, verbose_name='توضیحات')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')),
                ('ai_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wallet_entries', to='order.aiproductorder', verbose_name='سفارش محصول هوش مصنوعی')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_wallet_entries', to=settings.AUTH_USER_MODEL, verbose_name='ثبت کننده (خالی = سیستم)')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wallet_entries', to='order.order', verbose_name='سفارش')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wallet_entries', to='accounting.payment', verbose_name='پرداخت')),
                ('reverses', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reversed_by', to='accounting.walletentry', verbose_name='معکوسِ سند')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wallet_entries', to=settings.AUTH_USER_MODEL, verbose_name='صاحب کیف پول')),
            ],
            options={
                'verbose_name': 'سند کیف پول',
                'verbose_name_plural': 'اسناد کیف پول',
                'ordering': ('-created_at', '-id'),
                'indexes': [models.Index(fields=['user', '-created_at'], name='wallet_entry_user_idx')],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='wallet_entry_amount_gt_0'),
                    models.UniqueConstraint(condition=models.Q(('kind', 'deposit')), fields=('payment',), name='unique_deposit_per_payment'),
                    models.UniqueConstraint(condition=models.Q(('kind', 'course_purchase')), fields=('order',), name='unique_purchase_per_order'),
                    models.UniqueConstraint(condition=models.Q(('kind', 'ai_purchase')), fields=('ai_order',), name='unique_purchase_per_ai_order'),
                ],
            },
        ),
    ]
