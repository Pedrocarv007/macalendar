from rest_framework import serializers
from .models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    event_type_label = serializers.CharField(source='get_event_type_display', read_only=True)
    is_external = serializers.SerializerMethodField()
    affected_restaurants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    affected_restaurant_names = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'event_type', 'event_type_label', 'restaurant', 'restaurant_name',
            'affected_restaurants', 'affected_restaurant_names',
            'created_by', 'created_by_name', 'employee',
            'is_all_day', 'color', 'location', 'photo_path', 'photo_url', 'link',
            'is_recurring', 'recurrence_rule', 'event_metadata',
            'is_external',
            'is_posted', 'posted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at',
                            'created_by_name', 'restaurant_name', 'photo_url',
                            'color']

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else None

    def get_restaurant_name(self, obj):
        if obj.restaurant:
            return obj.restaurant.name
        affected = list(obj.affected_restaurants.all())
        if affected:
            return f'{len(affected)} restaurante(s) afetado(s)'
        return 'Global'

    def get_affected_restaurant_names(self, obj):
        return [restaurant.name for restaurant in obj.affected_restaurants.all()]

    def get_photo_url(self, obj):
        return obj.photo_path or None

    def get_is_external(self, obj):
        return bool((obj.event_metadata or {}).get('external_source'))

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'A data de fim não pode ser anterior à data de início.'
            })
        metadata = attrs.get(
            'event_metadata',
            getattr(self.instance, 'event_metadata', {}) or {},
        )
        impact_level = metadata.get('impact_level')
        if impact_level and impact_level not in {'low', 'medium', 'high'}:
            raise serializers.ValidationError({
                'event_metadata': 'O impacto deve ser baixo, médio ou alto.'
            })
        return attrs
