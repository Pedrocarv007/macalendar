from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'category', 'audience',
            'restaurant', 'user', 'created_by', 'created_by_name',
            'created_at', 'read_at', 'is_read',
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'is_read', 'created_by_name']

    def get_is_read(self, obj):
        return obj.is_read

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else None
