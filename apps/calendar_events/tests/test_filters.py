from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.http import QueryDict
from django.test import SimpleTestCase

from apps.calendar_events.models import CalendarEvent
from apps.calendar_events.views import CalendarEventViewSet


class CalendarEventFilterTests(SimpleTestCase):
    def queryset_for(self, query_string):
        queryset = MagicMock()
        queryset.prefetch_related.return_value = queryset
        queryset.exclude.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.none.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.order_by.return_value = queryset

        view = CalendarEventViewSet()
        view.action = "list"
        view.request = SimpleNamespace(
            user=SimpleNamespace(role="admin", restaurant_id=10),
            query_params=QueryDict(query_string),
        )
        with patch.object(
            CalendarEvent.objects,
            "select_related",
            return_value=queryset,
        ), patch(
            "apps.calendar_events.views.Restaurant.objects.filter",
        ) as restaurant_filter:
            restaurant_filter.return_value.exists.return_value = True
            result = view.get_queryset()
        self.assertIs(result, queryset)
        return queryset

    def test_multiple_event_types_are_combined_with_or(self):
        queryset = self.queryset_for("event_type=meeting&event_type=training")

        self.assertIn(
            call(event_type__in=["meeting", "training"]),
            queryset.filter.call_args_list,
        )

    def test_search_impact_and_restaurant_filters_are_all_applied(self):
        queryset = self.queryset_for(
            "restaurant_id=20&impact_level=high&search=estádio"
        )

        self.assertIn(
            call(event_metadata__impact_level="high"),
            queryset.filter.call_args_list,
        )
        # Visibility, search and restaurant scope are Q objects, while the
        # impact filter is a keyword call. Together they prove the filters compose.
        positional_filter_calls = [
            item for item in queryset.filter.call_args_list if item.args
        ]
        self.assertEqual(len(positional_filter_calls), 3)

    def test_suppressed_external_events_are_excluded_from_calendar(self):
        queryset = self.queryset_for("")

        visibility_calls = [
            item for item in queryset.filter.call_args_list
            if item.args and 'event_metadata__suppressed' in str(item.args[0])
        ]
        self.assertEqual(len(visibility_calls), 1)
        visibility_filter = str(visibility_calls[0].args[0])
        self.assertIn("event_metadata__suppressed", visibility_filter)
        self.assertIn("event_metadata__suppressed__isnull", visibility_filter)

    @patch("apps.calendar_events.views.ActivityLog.log")
    def test_deleting_external_event_marks_it_as_suppressed(self, activity_log):
        view = CalendarEventViewSet()
        view.request = SimpleNamespace(
            user=SimpleNamespace(role="admin", pk=91),
        )
        event = MagicMock(
            title="Evento importado",
            event_metadata={
                "external_source": "VisitOeiras",
                "source_key": "visitoeiras:42",
            },
        )

        view.perform_destroy(event)

        self.assertTrue(event.event_metadata["suppressed"])
        self.assertEqual(event.event_metadata["suppressed_by"], 91)
        event.save.assert_called_once_with(
            update_fields=["event_metadata", "updated_at"]
        )
        event.delete.assert_not_called()
        activity_log.assert_called_once()

    @patch("apps.calendar_events.views.ActivityLog.log")
    def test_deleting_manual_event_still_removes_database_row(self, activity_log):
        view = CalendarEventViewSet()
        view.request = SimpleNamespace(
            user=SimpleNamespace(role="admin", pk=91),
        )
        event = MagicMock(title="Evento manual", event_metadata={})

        view.perform_destroy(event)

        event.delete.assert_called_once_with()
        event.save.assert_not_called()
        activity_log.assert_called_once()

    def test_inventory_only_restaurant_filter_returns_no_events(self):
        queryset = MagicMock()
        queryset.prefetch_related.return_value = queryset
        queryset.exclude.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.none.return_value = queryset

        view = CalendarEventViewSet()
        view.action = "list"
        view.request = SimpleNamespace(
            user=SimpleNamespace(role="admin", restaurant_id=10),
            query_params=QueryDict("restaurant_id=999"),
        )
        with patch.object(
            CalendarEvent.objects,
            "select_related",
            return_value=queryset,
        ), patch(
            "apps.calendar_events.views.Restaurant.objects.filter",
        ) as restaurant_filter:
            restaurant_filter.return_value.exists.return_value = False
            result = view.get_queryset()

        self.assertIs(result, queryset)
        queryset.none.assert_called_once_with()
        self.assertEqual(queryset.filter.call_count, 1)

    @patch("django.db.models.Model.save")
    def test_model_replaces_arbitrary_event_color(self, base_save):
        event = CalendarEvent(event_type="meeting", color="#000000")

        event.save()

        self.assertEqual(event.color, CalendarEvent.EVENT_COLORS["meeting"])
        base_save.assert_called_once()
