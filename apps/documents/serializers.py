from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'template_name',
            'employee', 'employee_name', 'worker', 'worker_name',
            'restaurant', 'restaurant_name', 'created_by', 'created_by_name',
            'content', 'filename', 'file_path', 'file_size', 'file_size_display',
            'file_extension', 'description', 'tags', 'is_public', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'created_by_name', 'restaurant_name', 'employee_name',
            'worker_name', 'file_size_display',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else None

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else None

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else None

    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker else None

    def get_file_size_display(self, obj):
        if not obj.file_size:
            return None
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
