from rest_framework import serializers
from .models import Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    employees_count = serializers.SerializerMethodField()
    workers_count = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'sso_id', 'name', 'code', 'address', 'phone', 'email',
            'capacity', 'opening_hours', 'description',
            'photo_filename', 'photo_url', 'manager',
            'is_active', 'employees_count', 'workers_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'sso_id', 'name', 'code', 'created_at', 'updated_at', 'photo_url', 'employees_count', 'workers_count']

    def get_photo_url(self, obj):
        return obj.photo_url

    def get_employees_count(self, obj):
        return obj.employees.filter(is_active=True).count()

    def get_workers_count(self, obj):
        # Workers agora geridos pelo SSO — conta via SSO DB por código de restaurante
        from apps.workers.models import Worker, SSORestaurant
        sso_rest = SSORestaurant.objects.filter(name__iexact=obj.name).first()
        if sso_rest:
            return Worker.objects.filter(restaurant_id=sso_rest.id, is_active=True).count()
        return 0
