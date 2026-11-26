import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.map_view import build_map_days
from core.trip_models import RoutePart, RouteSnapshot
from core.trip_routes import enrich_trip_routes
from core.trip_service import plan_trip
from core.trip_store import save_itinerary, load_itinerary
import test_trip_persistence_edit as fixtures


class TripRoutesTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.trip = fixture.trip
        self.route = RouteSnapshot("ok", "amap", fixture.now, 100, 61,
                                   [RoutePart("walking", [[120, 30], [120.1, 30.1]])])

    def test_service_enriches_after_generation_and_persists(self):
        with (patch("core.trip_service.parse_trip_request", return_value=self.trip.request),
              patch("core.trip_service.gather_trip_sources", return_value=(self.trip.places, [], "evidence")),
              patch("core.trip_service.generate_itinerary", return_value=self.trip) as generate,
              patch("core.trip_routes.query_amap_route", return_value=self.route) as query):
            result = plan_trip(object(), {})
        generate.assert_called_once()
        query.assert_called_once_with(self.trip.places[0], self.trip.places[1], "walking")
        self.assertEqual(result.daily_plans[0].transport_segments[0].estimated_minutes, 2)
        self.assertIsNone(self.trip.daily_plans[0].transport_segments[0].route)
        self.assertEqual(build_map_days(result), build_map_days(self.trip))
        with TemporaryDirectory() as directory:
            db = Path(directory) / "trips.db"
            save_itinerary("test", result, db)
            self.assertEqual(load_itinerary("test", db), result)

    def test_failed_query_clears_model_minutes(self):
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="超时")
        day = self.trip.daily_plans[0]
        trip = replace(self.trip, daily_plans=[replace(day, transport_segments=[replace(
            day.transport_segments[0], estimated_minutes=99)])])
        with patch("core.trip_routes.query_amap_route", return_value=failed):
            result = enrich_trip_routes(trip)
        segment = result.daily_plans[0].transport_segments[0]
        self.assertIsNone(segment.estimated_minutes)
        self.assertEqual(segment.route.failure_reason, "超时")

    def test_modes_are_explicit_and_mixed_results_are_independent(self):
        day = self.trip.daily_plans[0]
        days = []
        for index, mode in enumerate(("自驾", "公交", "火车", "步行或打车")):
            plan_date = day.plan_date + timedelta(days=index)
            days.append(replace(day, day_number=index + 1, plan_date=plan_date,
                                weather=replace(day.weather, forecast_date=plan_date),
                                transport_segments=[replace(day.transport_segments[0], mode=mode, estimated_minutes=20)]))
        trip = replace(self.trip, request=replace(self.trip.request, days=4), daily_plans=days)
        with patch("core.trip_routes.query_amap_route", return_value=self.route) as query:
            result = enrich_trip_routes(trip)
        self.assertEqual(query.call_count, 1)
        self.assertEqual(query.call_args.args[2], "driving")
        self.assertEqual([d.transport_segments[0].route.status for d in result.daily_plans],
                         ["ok", "failed", "failed", "failed"])
        self.assertTrue(all(d.transport_segments[0].estimated_minutes is None for d in result.daily_plans[1:]))

    def test_single_activity_needs_no_query(self):
        day = replace(self.trip.daily_plans[0], activities=self.trip.daily_plans[0].activities[:1], transport_segments=[])
        with patch("core.trip_routes.query_amap_route") as query:
            result = enrich_trip_routes(replace(self.trip, daily_plans=[day]))
        query.assert_not_called()
        self.assertEqual(result.daily_plans[0].transport_segments, [])
