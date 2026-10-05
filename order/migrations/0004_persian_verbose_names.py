from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_aiproductorder_paid_at'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ordercomment',
            options={'verbose_name': 'توضیح سفارش', 'verbose_name_plural': 'توضیحات سفارش'},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'verbose_name': 'سفارش', 'verbose_name_plural': 'سفارش\u200cها', 'permissions': [('approve_order', 'Can approve order'), ('reject_order', 'Can reject order'), ('view_own_sales_report', 'Can view own sales report'), ('view_own_sales_commission', 'Can view own sales commission'), ('view_all_orders', 'Can view all orders'), ('change_any_order', 'Can change any order')]},
        ),
        migrations.AlterModelOptions(
            name='requestedproduct',
            options={'verbose_name': 'دورهٔ سفارش', 'verbose_name_plural': 'دوره\u200cهای سفارش'},
        ),
        migrations.AlterModelOptions(
            name='aiproductorder',
            options={'verbose_name': 'سفارش محصول هوش مصنوعی', 'verbose_name_plural': 'سفارش\u200cهای محصولات هوش مصنوعی', 'ordering': ['-created_at']},
        ),
    ]
