from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_events", "0002_calendar_event_local_impact"),
        ("restaurants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendarevent",
            name="affected_restaurants",
            field=models.ManyToManyField(
                blank=True,
                related_name="traffic_impact_events",
                to="restaurants.restaurant",
            ),
        ),
    ]
