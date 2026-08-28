from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.calendar_events.external_events import (
    ExternalEventCandidate,
    _parse_ics_events,
    analyse_event_impact,
    classify_impact,
    fetch_tmdb_cinema_releases,
    sync_visit_oeiras_events,
)


def restaurant(pk, name):
    return SimpleNamespace(id=pk, name=name, address="")


RESTAURANTS = [
    restaurant(1, "McDonald's Oeiras A5"),
    restaurant(2, "McDonald's Oeiras Mar"),
    restaurant(3, "McDonald's Paço de Arcos"),
    restaurant(4, "McDonald's Oeiras Parque"),
    restaurant(5, "McDonald's Tagus Park"),
    restaurant(6, "McDonald's Algés"),
]


class ExternalEventRulesTests(SimpleTestCase):
    @patch.dict(
        "os.environ",
        {
            "TMDB_API_READ_TOKEN": "test-token",
            "TMDB_MIN_POPULARITY": "20",
            "TMDB_MAX_RELEASES": "10",
        },
    )
    def test_tmdb_premiere_is_a_high_impact_all_store_event(self):
        response = MagicMock()
        response.json.return_value = {
            "page": 1,
            "total_pages": 1,
            "results": [{
                "id": 987,
                "title": "Grande Estreia",
                "original_title": "Big Premiere",
                "overview": "Um grande filme para toda a família.",
                "release_date": "2026-08-20",
                "popularity": 75.4,
                "poster_path": "/poster.jpg",
            }],
        }
        session = MagicMock()
        session.get.return_value = response

        releases = fetch_tmdb_cinema_releases(
            start_date=datetime(2026, 8, 1, tzinfo=dt_timezone.utc).date(),
            end_date=datetime(2026, 8, 31, tzinfo=dt_timezone.utc).date(),
            session=session,
        )

        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0].source_key, "tmdb:987")
        self.assertEqual(releases[0].category, "cinema")
        self.assertIn("Estreia no cinema", releases[0].title)
        analysis = analyse_event_impact(releases[0], RESTAURANTS)
        self.assertEqual(analysis["impact_level"], "high")
        self.assertEqual(
            analysis["matched_restaurant_ids"],
            [item.id for item in RESTAURANTS],
        )
        request = session.get.call_args
        self.assertEqual(request.kwargs["params"]["region"], "PT")
        self.assertEqual(request.kwargs["params"]["with_release_type"], "3|2")
        self.assertEqual(
            request.kwargs["headers"]["Authorization"],
            "Bearer test-token",
        )

    def test_football_is_high_impact_category(self):
        level, category = classify_impact({
            "title": "Jogo de futebol em Lisboa", "description": "",
            "categories": [], "tags": [],
        })
        self.assertEqual(level, "high")
        self.assertEqual(category, "sports")

    def test_luz_match_impacts_a5_regardless_of_teams(self):
        candidate = ExternalEventCandidate(
            source="Liga Portugal", source_key="match:1",
            title="Jogo: Equipa A - Equipa B",
            start=datetime(2026, 8, 9, 19, 30, tzinfo=dt_timezone.utc),
            end=datetime(2026, 8, 9, 21, 15, tzinfo=dt_timezone.utc),
            location="Estádio SL Benfica", category="sports",
        )
        analysis = analyse_event_impact(candidate, RESTAURANTS)

        self.assertEqual(analysis["impact_level"], "high")
        self.assertIn("A5", analysis["corridors"])
        self.assertEqual(analysis["restaurant_impacts"][0]["restaurant_name"], "McDonald's Oeiras A5")
        self.assertIn("regresso", analysis["peak_window_label"])

    def test_cascais_event_prioritises_oeiras_mar_and_paco(self):
        candidate = ExternalEventCandidate(
            source="VisitCascais", source_key="cascais:festas",
            title="Festas do Mar", start=datetime(2026, 8, 20, tzinfo=dt_timezone.utc),
            location="Baía de Cascais", category="festival",
            is_all_day=True, time_confirmed=False,
        )
        analysis = analyse_event_impact(candidate, RESTAURANTS)

        top_names = analysis["matched_restaurant_names"][:3]
        self.assertIn("McDonald's Oeiras Mar", top_names)
        self.assertIn("McDonald's Paço de Arcos", top_names)
        self.assertIn("horário oficial por confirmar", analysis["peak_window_label"].lower())

    def test_ics_parser_keeps_exact_football_times(self):
        payload = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:fixture-10108
DTSTART:20260809T193000Z
DTEND:20260809T211500Z
LOCATION:Estádio SL Benfica
SUMMARY:SL Benfica - Académico
URL:https://www.ligaportugal.pt/match/20262027/ligaportugalbetclic/1/8
END:VEVENT
END:VCALENDAR
"""
        events = _parse_ics_events(payload, "https://example.test/team.ics")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Jogo: SL Benfica - Académico")
        self.assertTrue(events[0].time_confirmed)
        self.assertEqual(events[0].location, "Estádio SL Benfica")

    def test_ics_parser_limits_football_without_time_to_one_day(self):
        payload = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:fixture-without-time
DTSTART;VALUE=DATE:20260809
DTEND;VALUE=DATE:20260812
SUMMARY:Jogo por confirmar
END:VEVENT
END:VCALENDAR
"""

        events = _parse_ics_events(payload, "https://example.test/team.ics")

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].is_all_day)
        self.assertEqual(events[0].end - events[0].start, timedelta(days=1))


class ExternalEventSyncTests(SimpleTestCase):
    @patch("apps.calendar_events.external_events.CalendarEvent.objects")
    @patch("apps.calendar_events.external_events.Restaurant.objects")
    @patch("apps.calendar_events.external_events.fetch_visit_oeiras_events")
    def test_sync_creates_targeted_event_with_affected_restaurants(
        self, fetch, restaurant_objects, event_objects,
    ):
        target = restaurant(42, "McDonald's Paço de Arcos")
        restaurant_objects.filter.return_value.order_by.return_value = [target]
        event_objects.filter.return_value.first.return_value = None
        created_event = MagicMock()
        event_objects.create.return_value = created_event
        fetch.return_value = [{
            "id": 123, "title": "Concerto junto à praia",
            "description": "<p>Concerto para toda a família.</p>",
            "start_date": "2026-08-15 21:00:00", "end_date": "2026-08-15 23:00:00",
            "all_day": False, "url": "https://visitoeiras.com/event/concerto/",
            "venue": {"venue": "Praia de Paço de Arcos"},
            "categories": [{"name": "Música"}], "tags": [],
        }]

        result = sync_visit_oeiras_events()

        self.assertEqual(result["created"], 1)
        values = event_objects.create.call_args.kwargs
        self.assertIsNone(values["restaurant"])
        self.assertEqual(values["event_type"], "local_impact")
        self.assertEqual(values["event_metadata"]["external_source"], "VisitOeiras")
        created_event.affected_restaurants.set.assert_called_once_with([42])

    @patch("apps.calendar_events.external_events.CalendarEvent.objects")
    @patch("apps.calendar_events.external_events.Restaurant.objects")
    @patch("apps.calendar_events.external_events.fetch_visit_oeiras_events")
    def test_sync_does_not_restore_suppressed_event(
        self, fetch, restaurant_objects, event_objects,
    ):
        restaurant_objects.filter.return_value.order_by.return_value = RESTAURANTS
        suppressed_event = MagicMock(event_metadata={
            "external_source": "VisitOeiras",
            "source_key": "visitoeiras:123",
            "suppressed": True,
        })
        event_objects.filter.return_value.first.return_value = suppressed_event
        fetch.return_value = [{
            "id": 123, "title": "Concerto junto à praia",
            "description": "Concerto para toda a família.",
            "start_date": "2026-08-15 21:00:00",
            "end_date": "2026-08-15 23:00:00",
            "all_day": False,
            "url": "https://visitoeiras.com/event/concerto/",
            "venue": {"venue": "Praia de Paço de Arcos"},
            "categories": [{"name": "Música"}], "tags": [],
        }]

        result = sync_visit_oeiras_events()

        self.assertEqual(result["suppressed"], 1)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
        event_objects.create.assert_not_called()
        suppressed_event.save.assert_not_called()
