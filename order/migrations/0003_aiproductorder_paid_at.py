from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiproductorder',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='زمان پرداخت'),
        ),
        migrations.AddIndex(
            model_name='aiproductorder',
            index=models.Index(fields=['videopol_payment_id'], name='ai_order_videopol_payment_idx'),
        ),
    ]
