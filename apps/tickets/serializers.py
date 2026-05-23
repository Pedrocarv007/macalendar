from rest_framework import serializers
from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'subject', 'message', 'category', 'priority', 'status',
            'screenshot_filename', 'employee', 'employee_name',
            'restaurant', 'restaurant_name',
            'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = ['id', 'employee', 'created_at', 'updated_at', 'employee_name', 'restaurant_name']

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else None

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else None
