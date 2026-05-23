from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee, UserSettings


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ['name', 'email', 'role', 'restaurant', 'is_active']
    list_filter = ['role', 'is_active', 'restaurant']
    search_fields = ['name', 'email']
    ordering = ['name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informação Pessoal', {'fields': ('name', 'phone', 'birth_date', 'address', 'photo_filename')}),
        ('Trabalho', {'fields': ('role', 'employee_type', 'position', 'department', 'restaurant', 'hire_date')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'restaurant', 'password1', 'password2'),
        }),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'dark_mode', 'notifications_enabled', 'timezone']
