from django.db import transaction

from rest_framework import serializers

from course.models import Course
from order.models import (
    Order,
    RequestedProduct,
)


class RequestedProductInputSerializer(
    serializers.Serializer
):
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(
            can_sale=True,
        )
    )

    discount = serializers.DecimalField(
        max_digits=10,
        decimal_places=0,
        min_value=0,
        default=0,
    )

    def validate(self, attrs):
        course = attrs["course"]
        discount = attrs["discount"]

        if discount > course.price:
            raise serializers.ValidationError(
                {
                    "discount": (
                        "تخفیف نمی‌تواند بیشتر "
                        "از قیمت دوره باشد."
                    )
                }
            )

        return attrs


class RequestedProductSerializer(
    serializers.ModelSerializer
):
    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )

    final_price = serializers.SerializerMethodField()

    class Meta:
        model = RequestedProduct

        fields = [
            "id",
            "course",
            "course_title",
            "price",
            "discount",
            "final_price",
        ]

        read_only_fields = fields

    def get_final_price(
        self,
        obj,
    ):
        return obj.price - obj.discount


class OrderSerializer(
    serializers.ModelSerializer
):
    items = RequestedProductInputSerializer(
        many=True,
        write_only=True,
        required=False,
    )

    requested_products = (
        RequestedProductSerializer(
            many=True,
            read_only=True,
        )
    )

    class Meta:
        model = Order

        fields = [
            "id",
            "student",
            "seller",
            "created_by",
            "checked_by",
            "status",
            "is_deleted",
            "items",
            "requested_products",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "checked_by",
            "status",
            "is_deleted",
            "requested_products",
            "created_at",
            "updated_at",
        ]

    def validate_items(
        self,
        items,
    ):
        if not items:
            raise serializers.ValidationError(
                "سفارش باید حداقل یک محصول داشته باشد."
            )

        course_ids = [
            item["course"].pk
            for item in items
        ]

        if len(course_ids) != len(
            set(course_ids)
        ):
            raise serializers.ValidationError(
                "یک دوره نمی‌تواند چند بار "
                "در یک سفارش ثبت شود."
            )

        return items

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):
        items = validated_data.pop(
            "items",
            None,
        )

        if not items:
            raise serializers.ValidationError(
                {
                    "items": (
                        "سفارش باید حداقل "
                        "یک محصول داشته باشد."
                    )
                }
            )

        order = Order.objects.create(
            **validated_data
        )

        RequestedProduct.objects.bulk_create(
            [
                RequestedProduct(
                    order=order,
                    course=item["course"],

                    # قیمت از دیتابیس گرفته می‌شود،
                    # نه از request.
                    price=item[
                        "course"
                    ].price,

                    discount=item[
                        "discount"
                    ],
                )
                for item in items
            ]
        )

        return order

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        items = validated_data.pop(
            "items",
            None,
        )

        for attr, value in (
            validated_data.items()
        ):
            setattr(
                instance,
                attr,
                value,
            )

        instance.save()

        # اگر items اصلاً ارسال نشده باشد
        # محصولات قبلی دست نمی‌خورند.
        if items is None:
            return instance

        # اگر items ارسال شده، کل لیست
        # محصولات سفارش جایگزین می‌شود.
        instance.requested_products.all().delete()

        RequestedProduct.objects.bulk_create(
            [
                RequestedProduct(
                    order=instance,
                    course=item["course"],
                    price=item[
                        "course"
                    ].price,
                    discount=item[
                        "discount"
                    ],
                )
                for item in items
            ]
        )

        return instance