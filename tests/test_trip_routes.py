import unittest
from dataclasses import replace
from datetime import timedelta, time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.map_view import build_map_days
from core.trip_models import Activity, RoutePart, RouteSnapshot, TransportSegment
from core.trip_routes import enrich_trip_routes, refresh_edited_day_routes
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
        self.assertEqual(build_map_days(result)[0]["stops"], build_map_days(self.trip)[0]["stops"])
        self.assertEqual(build_map_days(result)[0]["segments"][0]["kind"], "route_snapshot")
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

    def test_edit_reuses_success_and_failure_with_mode_alias(self):
        for route, minutes in ((self.route, 2), (RouteSnapshot(
                "failed", "amap", self.trip.generated_at, failure_reason="超时"), None)):
            with self.subTest(status=route.status):
                day = self.trip.daily_plans[0]
                original = replace(self.trip, daily_plans=[replace(day, transport_segments=[
                    replace(day.transport_segments[0], route=route, estimated_minutes=minutes)])])
                edited_day = replace(day, activities=[replace(day.activities[0], description="新描述"),
                                                      day.activities[1]], transport_segments=[
                    replace(day.transport_segments[0], mode=" WALKING ", estimated_minutes=99)])
                with patch("core.trip_routes.query_amap_route") as query:
                    result = refresh_edited_day_routes(original, replace(self.trip, daily_plans=[edited_day]), 1)
                query.assert_not_called()
                segment = result.daily_plans[0].transport_segments[0]
                self.assertEqual((segment.route, segment.estimated_minutes), (route, minutes))
                self.assertIsNone(edited_day.transport_segments[0].route)

    def test_edit_queries_missing_snapshot_or_changed_mode_and_ignores_incoming_route(self):
        day = self.trip.daily_plans[0]
        for mode in ("步行", "自驾", "公交", "火车"):
            with self.subTest(mode=mode):
                incoming = replace(day, transport_segments=[replace(
                    day.transport_segments[0], mode=mode, route=self.route, estimated_minutes=2)])
                failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="超时")
                with patch("core.trip_routes.query_amap_route", return_value=failed) as query:
                    result = refresh_edited_day_routes(self.trip, replace(self.trip, daily_plans=[incoming]), 1)
                self.assertEqual(query.call_count, int(mode in ("步行", "自驾")))
                segment = result.daily_plans[0].transport_segments[0]
                self.assertEqual(segment.route.status, "failed")
                self.assertIsNone(segment.estimated_minutes)

    def test_removal_preserves_other_day_and_reuses_remaining_connection(self):
        day = self.trip.daily_plans[0]
        a, b = day.activities
        # 删除中间站后相邻活动同地点，无交通段；删除首站则保留原连接。
        old_segments = [TransportSegment("P1", "P2", "步行", 2, self.route),
                        TransportSegment("P2", "P1", "步行", 2, self.route)]
        original_day = replace(day, activities=[a, b, Activity("P1", "返回", time(13), time(14))],
                               transport_segments=old_segments)
        next_date = day.plan_date + timedelta(days=1)
        other_day = replace(day, day_number=2, plan_date=next_date,
                            weather=replace(day.weather, forecast_date=next_date))
        original = replace(self.trip, request=replace(self.trip.request, days=2),
                           daily_plans=[original_day, other_day])
        edited_day = replace(original_day, activities=[a, original_day.activities[2]], transport_segments=[])
        with patch("core.trip_routes.query_amap_route") as query:
            result = refresh_edited_day_routes(original, replace(original, daily_plans=[edited_day, other_day]), 1)
        query.assert_not_called()
        self.assertIs(result.daily_plans[1], other_day)
        edited_day = replace(original_day, activities=original_day.activities[1:],
                             transport_segments=[TransportSegment("P2", "P1", "步行")])
        with patch("core.trip_routes.query_amap_route") as query:
            result = refresh_edited_day_routes(original, replace(original, daily_plans=[edited_day, other_day]), 1)
        query.assert_not_called()
        self.assertEqual(result.daily_plans[0].transport_segments[0].route, self.route)

    def test_middle_removal_queries_bridge_without_reusing_adjacent_routes(self):
        day = self.trip.daily_plans[0]
        third = replace(self.trip.places[1], place_id="P3")
        original_day = replace(day, activities=[*day.activities, Activity("P3", "第三站", time(13), time(14))],
                               transport_segments=[TransportSegment("P1", "P2", "步行", 2, self.route),
                                                   TransportSegment("P2", "P3", "步行", 2, self.route)])
        original = replace(self.trip, places=[*self.trip.places, third], daily_plans=[original_day])
        edited_day = replace(original_day, activities=[original_day.activities[0], original_day.activities[2]],
                             transport_segments=[TransportSegment("P1", "P3", "步行")])
        with patch("core.trip_routes.query_amap_route", return_value=self.route) as query:
            result = refresh_edited_day_routes(original, replace(original, daily_plans=[edited_day]), 1)
        query.assert_called_once_with(original.places[0], third, "walking")
        self.assertEqual(result.daily_plans[0].transport_segments[0].to_place_id, "P3")

    def test_replacing_endpoint_queries_only_changed_connection(self):
        day = self.trip.daily_plans[0]
        third = replace(self.trip.places[1], place_id="P3")
        original = replace(self.trip, places=[*self.trip.places, third], daily_plans=[replace(
            day, transport_segments=[replace(day.transport_segments[0], route=self.route, estimated_minutes=2)])])
        edited_day = replace(day, activities=[day.activities[0], replace(day.activities[1], place_id="P3")],
                             transport_segments=[TransportSegment("P1", "P3", "步行", 99)])
        with patch("core.trip_routes.query_amap_route", return_value=self.route) as query:
            result = refresh_edited_day_routes(original, replace(original, daily_plans=[edited_day]), 1)
        query.assert_called_once_with(original.places[0], third, "walking")
        self.assertEqual(result.daily_plans[0].transport_segments[0].estimated_minutes, 2)
        self.assertEqual(original.daily_plans[0].transport_segments[0].to_place_id, "P2")
