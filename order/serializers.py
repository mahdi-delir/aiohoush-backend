from rest_framework import serializers

from order.models import Order


class OrderSerializer(
    serializers.ModelSerializer
):
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
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "checked_by",
            "status",
            "is_deleted",
            "created_at",
            "updated_at",
        ]