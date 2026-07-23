from django.test import SimpleTestCase

from apps.calendar_events.serializers import CalendarEventSerializer


class CalendarEventSerializerTests(SimpleTestCase):
    def test_end_date_cannot_precede_start_date(self):
        serializer = CalendarEventSerializer(data={
            "title": "Formação de equipa",
            "start_date": "2026-07-23T15:00:00+01:00",
            "end_date": "2026-07-23T14:00:00+01:00",
            "event_type": "training",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_valid_portuguese_event_is_accepted(self):
        serializer = CalendarEventSerializer(data={
            "title": "Reunião de operações",
            "start_date": "2026-07-23T14:00:00+01:00",
            "end_date": "2026-07-23T15:00:00+01:00",
            "event_type": "meeting",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
