from rest_framework import serializers
from .models import Worker, SSORestaurant

# Cache de restaurantes SSO carregado uma vez por request (evita N+1)
_REST_CACHE: dict = {}


def _get_rest_cache():
    if not _REST_CACHE:
        for r in SSORestaurant.objects.operational():
            _REST_CACHE[r.id] = r.name
    return _REST_CACHE


class SSORestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SSORestaurant
        fields = ['id', 'name', 'code', 'city']


class WorkerSerializer(serializers.ModelSerializer):
    name                = serializers.SerializerMethodField()
    photo_url           = serializers.SerializerMethodField()
    age                 = serializers.SerializerMethodField()
    days_until_birthday = serializers.SerializerMethodField()
    restaurant_name     = serializers.SerializerMethodField()

    class Meta:
        model  = Worker
        fields = [
            'id', 'first_name', 'last_name', 'name',
            'employee_number', 'email', 'phone',
            'birth_date', 'hire_date',
            'job_role', 'training_status',
            'photo_filename', 'photo_url', 'is_active',
            'restaurant_id', 'restaurant_name',
            'age', 'days_until_birthday',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return obj.name

    def get_photo_url(self, obj):
        return obj.photo_url

    def get_age(self, obj):
        return obj.age

    def get_days_until_birthday(self, obj):
        return obj.days_until_birthday

    def get_restaurant_name(self, obj):
        if not obj.restaurant_id:
            return '—'
        return _get_rest_cache().get(obj.restaurant_id, '—')
