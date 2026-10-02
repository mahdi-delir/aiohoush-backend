from django.db import models
from django.conf import settings
# Create your models here.

class BankAccount(models.Model):
    class BANK(models.TextChoices):
        SADERAT = 'saderat', 'صادرات'
        SEPAH = 'sepah', 'سپه'
        MELLI = 'melli','ملی'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name = 'صاحب حساب',
        related_name = 'bank_accounts'
    )
    bank = models.CharField(
        max_length = 10,
        verbose_name = 'نام بانک',
        choices = BANK.choices
    )
    card_number = models.CharField(
        max_length=16,
        verbose_name = 'شماره کارت'
    )
    sheba = models.CharField(
        max_length = 24,
        verbose_name = 'شماره شبا'
    )
    account_number = models.CharField(
        max_length = 24,
        verbose_name = 'شماره حساب'
    )

class Payment(models.Model):
    class GATEWAY(models.TextChoices):
        ZIBAL = 'zibal', 'زیبال'
        ZARINPAL = 'zarinpal', 'زرینپال'
        TRANSFER = 'transfer', 'انتقال'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.PROTECT,
        verbose_name = 'پرداخت کننده',
        related_name= 'payments'
    )

    bank = models.ForeignKey(
        'accounting.BankAccount',
        on_delete=models.PROTECT,
        verbose_name = 'حساب دریافت کننده',
        related_name = 'incomes'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name = 'کاربر ثبت کننده',
        related_name = 'created_payments',
        on_delete = models.PROTECT
    )

    order = models.ForeignKey(
        'order.Order',
        on_delete = models.PROTECT,
        verbose_name = 'سفارش',
        related_name = 'payments',
        blank = True,
        null = True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name = 'مبلغ واریزی'
    )

    paid_at = models.DateTimeField(
        verbose_name="تاریخ واریز",
    )

    tracking_code = models.CharField(
        max_length=255,
        verbose_name = 'کد پیگیری',
    )

    gateway = models.CharField(
        max_length=10,
        verbose_name="درگاه",
        choices=GATEWAY.choices,
    )

    user_card_digits = models.CharField(
        max_length = 4,
        verbose_name='چهار رقم آخر کارت کاربر',
        blank = True,
        null = True
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name="حذف شده؟",
    )

