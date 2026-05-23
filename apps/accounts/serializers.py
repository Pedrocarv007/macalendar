"""
Serializers for the accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSettings

Employee = get_user_model()


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            'timezone', 'notifications_enabled', 'email_notifications',
            'two_factor_enabled', 'auto_logout_enabled', 'session_timeout_minutes',
            'items_per_page', 'dark_mode',
        ]


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    photo_url = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    work_years = serializers.ReadOnlyField()
    is_birthday_today = serializers.ReadOnlyField()
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True, default='')

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'email', 'phone', 'role', 'employee_type',
            'position', 'department', 'restaurant', 'restaurant_name',
            'photo_url', 'age', 'work_years', 'is_birthday_today',
            'is_active', 'hire_date', 'birth_date', 'created_at',
        ]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Full serializer including settings."""
    photo_url = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    work_years = serializers.ReadOnlyField()
    days_until_birthday = serializers.ReadOnlyField()
    is_birthday_today = serializers.ReadOnlyField()
    next_birthday = serializers.ReadOnlyField()
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True, default='')
    settings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'email', 'phone', 'role', 'employee_type',
            'position', 'department', 'restaurant', 'restaurant_name',
            'address', 'notes', 'photo_filename', 'photo_url',
            'hire_date', 'birth_date',
            'age', 'work_years', 'days_until_birthday',
            'is_birthday_today', 'next_birthday',
            'is_active', 'is_staff',
            'created_at', 'updated_at',
            'settings',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_staff']

    def validate_email(self, value):
        request = self.context.get('request')
        qs = Employee.objects.filter(email__iexact=value)
        if request and request.method in ('PUT', 'PATCH') and self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An employee with this email already exists.')
        return value.lower()


class EmployeeCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Employee
        fields = [
            'name', 'email', 'password', 'phone', 'role', 'employee_type',
            'position', 'department', 'restaurant', 'address', 'notes',
            'hire_date', 'birth_date', 'is_active',
        ]

    def validate_email(self, value):
        if Employee.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An employee with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        employee = Employee(**validated_data)
        if password:
            employee.set_password(password)
        else:
            employee.set_unusable_password()
        employee.save()
        UserSettings.objects.get_or_create(user=employee)
        return employee


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for self-profile updates (limited fields)."""
    settings = UserSettingsSerializer(required=False)

    class Meta:
        model = Employee
        fields = [
            'name', 'phone', 'address', 'notes',
            'birth_date', 'position', 'department',
            'settings',
        ]

    def update(self, instance, validated_data):
        settings_data = validated_data.pop('settings', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if settings_data is not None:
            user_settings, _ = UserSettings.objects.get_or_create(user=instance)
            for attr, value in settings_data.items():
                setattr(user_settings, attr, value)
            user_settings.save()

        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
