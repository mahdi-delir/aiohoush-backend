import uuid

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
    class STATUS(models.TextChoices):
        PENDING = 'pending', 'در انتظار تأیید'
        CONFIRMED = 'confirmed', 'تأیید شده'
        REJECTED = 'rejected', 'رد شده'

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

    # برای پرداخت درگاهی خالی است (پول به حساب تسویهٔ درگاه می‌رود).
    bank = models.ForeignKey(
        'accounting.BankAccount',
        on_delete=models.PROTECT,
        verbose_name = 'حساب دریافت کننده',
        related_name = 'incomes',
        blank = True,
        null = True,
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

    # فقط پرداخت «تأیید شده» در موجودی کیف پول حساب می‌شود.
    # پرداخت درگاهی موقع ثبت تأیید شده است؛ بقیه را حسابداری تأیید می‌کند.
    status = models.CharField(
        max_length=10,
        choices=STATUS.choices,
        default=STATUS.PENDING,
        verbose_name='وضعیت',
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_payments',
        blank=True,
        null=True,
        verbose_name='بررسی کننده',
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='زمان بررسی',
    )

    ai_order = models.OneToOneField(
        'order.AIProductOrder',
        on_delete=models.PROTECT,
        related_name='payment',
        blank=True,
        null=True,
        verbose_name='سفارش محصول هوش مصنوعی',
    )

    top_up = models.OneToOneField(
        'accounting.WalletTopUp',
        on_delete=models.PROTECT,
        related_name='payment',
        blank=True,
        null=True,
        verbose_name='شارژ آنلاین کیف پول',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        verbose_name='زمان ثبت',
    )

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        permissions = [
            ('confirm_payment', 'Can confirm or reject payment'),
        ]

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.get_status_display()})"


class WalletEntry(models.Model):
    """یک سند در دفتر کیف پول.

    موجودی هر کاربر = مجموع بستانکار − مجموع بدهکار. اسناد هرگز ویرایش
    یا حذف نمی‌شوند؛ اصلاح با سند معکوس (reverses) انجام می‌شود.
    """

    class DIRECTION(models.TextChoices):
        CREDIT = 'credit', 'بستانکار (+)'
        DEBIT = 'debit', 'بدهکار (−)'

    class KIND(models.TextChoices):
        DEPOSIT = 'deposit', 'واریز'
        COURSE_PURCHASE = 'course_purchase', 'خرید دوره'
        AI_PURCHASE = 'ai_purchase', 'خرید محصول هوش مصنوعی'
        REVERSAL = 'reversal', 'سند معکوس'
        # انواع زیر در فازهای بعد (پنل فروشنده، مدیریت، حسابداری) ثبت می‌شوند.
        CHARGE = 'charge', 'شارژ از طرف آیوهوش'
        INSTALLMENT = 'installment', 'قسط'
        COMMISSION = 'commission', 'پورسانت'
        REWARD = 'reward', 'تشویق'
        PENALTY = 'penalty', 'جریمه'
        SALARY = 'salary', 'حقوق'
        SALARY_PAYOUT = 'salary_payout', 'پرداخت حقوق'
        WITHDRAWAL = 'withdrawal', 'برداشت'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet_entries',
        verbose_name='صاحب کیف پول',
    )

    direction = models.CharField(
        max_length=6,
        choices=DIRECTION.choices,
        verbose_name='جهت',
    )

    amount = models.PositiveBigIntegerField(
        verbose_name='مبلغ (ریال)',
    )

    kind = models.CharField(
        max_length=20,
        choices=KIND.choices,
        verbose_name='نوع',
    )

    title = models.CharField(
        max_length=255,
        verbose_name='عنوان (نمایش به کاربر)',
    )

    description = models.TextField(
        blank=True,
        verbose_name='توضیحات',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_wallet_entries',
        blank=True,
        null=True,
        verbose_name='ثبت کننده (خالی = سیستم)',
    )

    payment = models.ForeignKey(
        'accounting.Payment',
        on_delete=models.PROTECT,
        related_name='wallet_entries',
        blank=True,
        null=True,
        verbose_name='پرداخت',
    )

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.PROTECT,
        related_name='wallet_entries',
        blank=True,
        null=True,
        verbose_name='سفارش',
    )

    ai_order = models.ForeignKey(
        'order.AIProductOrder',
        on_delete=models.PROTECT,
        related_name='wallet_entries',
        blank=True,
        null=True,
        verbose_name='سفارش محصول هوش مصنوعی',
    )

    top_up = models.ForeignKey(
        'accounting.WalletTopUp',
        on_delete=models.PROTECT,
        related_name='wallet_entries',
        blank=True,
        null=True,
        verbose_name='شارژ آنلاین',
    )

    reverses = models.OneToOneField(
        'self',
        on_delete=models.PROTECT,
        related_name='reversed_by',
        blank=True,
        null=True,
        verbose_name='معکوسِ سند',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='زمان ثبت',
    )

    class Meta:
        verbose_name = 'سند کیف پول'
        verbose_name_plural = 'اسناد کیف پول'
        ordering = ('-created_at', '-id')
        indexes = [
            models.Index(
                fields=['user', '-created_at'],
                name='wallet_entry_user_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='wallet_entry_amount_gt_0',
            ),
            # هر پرداخت فقط یک بار واریز ثبت می‌کند.
            models.UniqueConstraint(
                fields=['payment'],
                condition=models.Q(kind='deposit'),
                name='unique_deposit_per_payment',
            ),
            # هر سفارش فقط یک سند خرید دارد.
            models.UniqueConstraint(
                fields=['order'],
                condition=models.Q(kind='course_purchase'),
                name='unique_purchase_per_order',
            ),
            models.UniqueConstraint(
                fields=['ai_order'],
                condition=models.Q(kind='ai_purchase'),
                name='unique_purchase_per_ai_order',
            ),
        ]

    @property
    def signed_amount(self) -> int:
        return (
            self.amount
            if self.direction == self.DIRECTION.CREDIT
            else -self.amount
        )

    def __str__(self):
        sign = '+' if self.direction == self.DIRECTION.CREDIT else '−'
        return f"{self.user} {sign}{self.amount} {self.get_kind_display()}"


class WalletTopUp(models.Model):
    """درخواست شارژ آنلاین کیف پول از طریق درگاه (ویدوپل).

    بعد از تأیید پرداخت، یک Payment تأییدشده و سند واریز ساخته می‌شود.
    """

    class STATUS(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت شده"
        FAILED = "failed", "ناموفق"
        CANCELLED = "cancelled", "لغو شده"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet_top_ups",
        verbose_name="کاربر",
    )

    amount_rial = models.PositiveBigIntegerField(
        verbose_name="مبلغ (ریال)",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS.choices,
        default=STATUS.PENDING,
        verbose_name="وضعیت",
    )

    videopol_payment_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="شناسه پرداخت ویدوپل",
    )

    payment_url = models.URLField(
        blank=True,
        verbose_name="آدرس پرداخت",
    )

    reference_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="شناسه مرجع پرداخت",
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="زمان پرداخت",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ به‌روزرسانی",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "شارژ آنلاین کیف پول"
        verbose_name_plural = "شارژهای آنلاین کیف پول"

    def __str__(self):
        return f"{self.user} - {self.amount_rial}"
