from django.db import models
from django.conf import settings
import uuid

class OrderComment(models.Model):
    order = models.ForeignKey(
        'order.Order',
        verbose_name='سفارش',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='کاربر کامنت دهنده',
        related_name = 'order_comments',
        on_delete = models.PROTECT
    )
    comment = models.TextField(
        verbose_name = 'توضیح سفارش'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name = 'تاریخ ایجاد'
    )

    class Meta:
        verbose_name = "توضیح سفارش"
        verbose_name_plural = "توضیحات سفارش"

class Order(models.Model):
    class STATUS(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        APPROVED = 'approved', 'تأیید شده'
        REJECTED = 'rejected', 'رد شده'
        DRAFT = 'draft', 'پیش نویس'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name = 'دانشجو',
        related_name='orders'
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.PROTECT,
        verbose_name = 'فروشنده',
        related_name= 'sales',
        blank = True,
        null = True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.PROTECT,
        verbose_name='کاربر ثبت کننده سفارش',
        related_name='created_orders'
    )

    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.PROTECT,
        verbose_name='کاربر بررسی کننده',
        related_name='checked_orders',
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        verbose_name='وضعیت',
        default = STATUS.PENDING,
        choices = STATUS.choices
    )

    is_deleted = models.BooleanField(
        verbose_name = 'پاک شده؟',
        default = False
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name = 'زمان ایجاد'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name = 'آخرین ویرایش'
    )
    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"

        permissions = [
            (
                "approve_order",
                "Can approve order",
            ),
            (
                "reject_order",
                "Can reject order",
            ),
            (
                "view_own_sales_report",
                "Can view own sales report",
            ),
            (
                "view_own_sales_commission",
                "Can view own sales commission",
            ),
             (
                "view_all_orders",
                "Can view all orders",
            ),
            (
                "change_any_order",
                "Can change any order",
            ),
        ]

class RequestedProduct(models.Model):
    order = models.ForeignKey(
        'order.Order',
        on_delete = models.CASCADE,
        verbose_name = 'سفارش',
        related_name = 'requested_products'
    )
    course = models.ForeignKey(
        'course.Course',
        on_delete=models.PROTECT,
        verbose_name = 'دوره',
        related_name="requested_products",

    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name = 'مبلغ دوره هنگام ثبت سفارش'
    )
    discount = models.DecimalField(
        max_digits = 10,
        decimal_places=0,
        verbose_name = 'تخفیف',
        default=0
    )
    class Meta:
        verbose_name = "دورهٔ سفارش"
        verbose_name_plural = "دوره‌های سفارش"

        constraints = [
            models.UniqueConstraint(
                fields=["order", "course"],
                name="unique_course_per_order",
            ),

            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="requested_product_price_gte_0",
            ),

            models.CheckConstraint(
                condition=models.Q(discount__gte=0),
                name="requested_product_discount_gte_0",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    discount__lte=models.F("price"),
                ),
                name="requested_product_discount_lte_price",
            ),
        ]

class AIProductOrder(models.Model):
    class STATUS(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت شده"
        FAILED = "failed", "ناموفق"
        CANCELLED = "cancelled", "لغو شده"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه سفارش محصول هوش مصنوعی"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ai_product_orders",
        verbose_name="کاربر"
    )

    product_code = models.CharField(
        max_length=80,
        verbose_name='کد محصول',
    )

    amount_rial = models.PositiveBigIntegerField(
        verbose_name='مبلغ سفارش (ریال)',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS.choices,
        default=STATUS.PENDING,
        verbose_name='وضعیت سفارش',
    )

    videopol_payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='شناسه پرداخت ویدوپول'
    )

    payment_url = models.URLField(
        blank=True,
        verbose_name='آدرس پرداخت'
    )

    reference_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='شناسه مرجع پرداخت'
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='زمان پرداخت'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ به‌روزرسانی'
    )

    class Meta:
        verbose_name = "سفارش محصول هوش مصنوعی"
        verbose_name_plural = "سفارش‌های محصولات هوش مصنوعی"

        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["videopol_payment_id"],
                name="ai_order_videopol_payment_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.product_code}"