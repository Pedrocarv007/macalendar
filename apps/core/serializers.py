from rest_framework import serializers
from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'activity_type', 'description', 'user', 'user_name',
            'restaurant', 'restaurant_name', 'target_id', 'target_type', 'created_at',
        ]

    def get_user_name(self, obj):
        return obj.user.name if obj.user else None

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else None
