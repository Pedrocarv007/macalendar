from django.contrib import admin
from .models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'start_date', 'restaurant', 'created_by']
    list_filter = ['event_type', 'restaurant']
    search_fields = ['title']
    date_hierarchy = 'start_date'
