from django.db import migrations, models


EVENT_COLORS = {
    "meeting": "#93C5FD",
    "birthday": "#FFBC0D",
    "holiday": "#FCA5A5",
    "shift": "#CBD5E1",
    "training": "#99F6E4",
    "post": "#F9A8D4",
    "mystery_challenge": "#C4B5FD",
    "mystery_answer": "#86EFAC",
    "local_impact": "#FDBA74",
    "other": "#D4D4D8",
}


def normalize_event_colors(apps, schema_editor):
    CalendarEvent = apps.get_model("calendar_events", "CalendarEvent")
    for event_type, color in EVENT_COLORS.items():
        CalendarEvent.objects.filter(event_type=event_type).update(color=color)


class Migration(migrations.Migration):
    dependencies = [
        ("calendar_events", "0003_calendarevent_affected_restaurants"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calendarevent",
            name="color",
            field=models.CharField(default="#93C5FD", max_length=7),
        ),
        migrations.RunPython(normalize_event_colors, migrations.RunPython.noop),
    ]
