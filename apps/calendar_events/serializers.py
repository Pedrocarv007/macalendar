from rest_framework import serializers
from .models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    event_type_label = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'event_type', 'event_type_label', 'restaurant', 'restaurant_name',
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

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'A data de fim não pode ser anterior à data de início.'
            })
        return attrs
