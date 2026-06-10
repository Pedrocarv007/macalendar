from rest_framework import serializers
from .models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'event_type', 'restaurant', 'restaurant_name',
            'created_by', 'created_by_name', 'employee',
            'is_all_day', 'color', 'location', 'photo_path', 'photo_url', 'link',
            'is_recurring', 'recurrence_rule', 'event_metadata',
            'is_posted', 'posted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at',
                            'created_by_name', 'restaurant_name', 'photo_url']

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else None

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else 'Global'

    def get_photo_url(self, obj):
        return obj.photo_path or None
