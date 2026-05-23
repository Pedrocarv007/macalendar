from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'status', 'restaurant', 'created_by', 'created_at']
    list_filter = ['document_type', 'status', 'restaurant']
    search_fields = ['title']
