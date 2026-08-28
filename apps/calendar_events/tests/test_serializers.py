from django.test import SimpleTestCase

from apps.calendar_events.models import CalendarEvent
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

    def test_custom_color_is_not_accepted_from_the_client(self):
        serializer = CalendarEventSerializer(data={
            "title": "Reunião com cor manipulada",
            "start_date": "2026-07-23T14:00:00+01:00",
            "event_type": "meeting",
            "color": "#000000",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("color", serializer.validated_data)


class CalendarEventColorTests(SimpleTestCase):
    def test_legacy_operational_types_are_not_exposed_as_ui_options(self):
        visible = {item["value"] for item in CalendarEvent.event_type_options()}

        self.assertTrue(CalendarEvent.HIDDEN_EVENT_TYPE_OPTIONS.isdisjoint(visible))
        self.assertIn("local_impact", visible)

    def test_every_event_type_has_one_unique_canonical_color(self):
        option_values = {item["value"] for item in CalendarEvent.event_type_options()}
        choice_values = {value for value, _label in CalendarEvent.EVENT_TYPES}

        self.assertEqual(
            option_values,
            choice_values - CalendarEvent.HIDDEN_EVENT_TYPE_OPTIONS,
        )
        self.assertEqual(len(CalendarEvent.EVENT_COLORS), len(choice_values))
        self.assertEqual(
            len(set(CalendarEvent.EVENT_COLORS.values())),
            len(CalendarEvent.EVENT_COLORS),
        )

    def test_unknown_event_type_uses_other_color(self):
        self.assertEqual(
            CalendarEvent.color_for_type("unknown"),
            CalendarEvent.EVENT_COLORS["other"],
        )
