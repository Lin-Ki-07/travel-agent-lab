import unittest
from dataclasses import replace
from datetime import timedelta, time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.map_view import build_map_days
from core.trip_models import Activity, RoutePart, RouteSnapshot, TransportSegment
from core.trip_routes import enrich_trip_routes, refresh_edited_day_routes, complete_missing_routes
from core.trip_service import plan_trip
from core.trip_store import save_itinerary, load_itinerary
import test_trip_persistence_edit as fixtures


class TripRoutesTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.trip = replace(fixture.trip, request=replace(fixture.trip.request, preferences=["步行"]))
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

    def test_single_activity_needs_no_query(self):
        day = replace(self.trip.daily_plans[0], activities=self.trip.daily_plans[0].activities[:1], transport_segments=[])
        with patch("core.trip_routes.query_amap_route") as query:
            result = enrich_trip_routes(replace(self.trip, daily_plans=[day]))
        query.assert_not_called()
        self.assertEqual(result.daily_plans[0].transport_segments, [])

    def test_transit_aliases_pass_endpoint_codes_and_day_date_once(self):
        day = self.trip.daily_plans[0]
        places = [replace(self.trip.places[0], citycode="010"),
                  replace(self.trip.places[1], citycode="0532")]
        route = replace(self.route, parts=[replace(self.route.parts[0], mode="transit")])
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="超时")
        for mode in ("公交", "公交车", "公共交通", "地铁", " BUS ", "subway", "metro", "transit"):
            for snapshot in (route, failed):
                with self.subTest(mode=mode, status=snapshot.status):
                    trip = replace(self.trip, request=replace(self.trip.request, preferences=[]), places=places, daily_plans=[replace(day, transport_segments=[
                        replace(day.transport_segments[0], mode=mode, estimated_minutes=99)])])
                    with patch("core.trip_routes.query_amap_route", return_value=snapshot) as query:
                        result = enrich_trip_routes(trip)
                    query.assert_called_once_with(places[0], places[1], "transit",
                        origin_citycode="010", destination_citycode="0532", departure_date=day.plan_date)
                    segment = result.daily_plans[0].transport_segments[0]
                    self.assertEqual((segment.mode, segment.route, segment.estimated_minutes),
                                     ("公共交通", snapshot, 2 if snapshot.status == "ok" else None))

    def test_transit_missing_either_code_tries_driving_once(self):
        day = self.trip.daily_plans[0]
        for codes in ((None, "010"), ("010", None), (None, None)):
            with self.subTest(codes=codes):
                trip = replace(self.trip, request=replace(self.trip.request, preferences=[]), places=[replace(p, citycode=c) for p, c in zip(self.trip.places, codes)],
                    daily_plans=[replace(day, transport_segments=[replace(day.transport_segments[0], mode="公交")])])
                with patch("core.trip_routes.query_amap_route", return_value=RouteSnapshot(
                        "failed", "amap", self.trip.generated_at, failure_reason="超时")) as query:
                    segment = enrich_trip_routes(trip).daily_plans[0].transport_segments[0]
                query.assert_called_once_with(trip.places[0], trip.places[1], "driving")
                self.assertEqual(segment.route.status, "failed")
                self.assertEqual(segment.route.failure_reason, "超时")
                self.assertEqual(segment.route.parts, [])
                self.assertIsNone(segment.estimated_minutes)

    def test_edit_transit_queries_missing_snapshot_then_reuses_alias_snapshot(self):
        day = self.trip.daily_plans[0]
        original = replace(self.trip, request=replace(self.trip.request, preferences=[]), places=[replace(p, citycode="010") for p in self.trip.places])
        edited = replace(original, daily_plans=[replace(day, transport_segments=[
            replace(day.transport_segments[0], mode="地铁")])])
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="无可用方案")
        transit = replace(self.route, parts=[replace(self.route.parts[0], mode="transit")])
        for snapshot in (transit, failed):
            with self.subTest(status=snapshot.status):
                with patch("core.trip_routes.query_amap_route", return_value=snapshot) as query:
                    result = refresh_edited_day_routes(original, edited, 1)
                query.assert_called_once_with(original.places[0], original.places[1], "transit",
                    origin_citycode="010", destination_citycode="010", departure_date=day.plan_date)
                alias = replace(edited, daily_plans=[replace(edited.daily_plans[0], transport_segments=[
                    replace(edited.daily_plans[0].transport_segments[0], mode=" METRO ")])])
                with patch("core.trip_routes.query_amap_route") as query:
                    reused = refresh_edited_day_routes(result, alias, 1)
                query.assert_not_called()
                self.assertEqual(reused.daily_plans[0].transport_segments[0].route, snapshot)

    def test_taxi_aliases_query_driving_once_and_preserve_requested_mode(self):
        day = self.trip.daily_plans[0]
        driving = replace(self.route, parts=[replace(self.route.parts[0], mode="driving")])
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="超时")
        for mode in ("打车", "出租车", " TAXI "):
            for route in (driving, failed):
                with self.subTest(mode=mode, status=route.status):
                    trip = replace(self.trip, request=replace(self.trip.request, preferences=["自驾"]), daily_plans=[replace(day, transport_segments=[
                        replace(day.transport_segments[0], mode=mode, estimated_minutes=99)])])
                    with patch("core.trip_routes.query_amap_route", return_value=route) as query:
                        result = enrich_trip_routes(trip)
                    query.assert_called_once_with(trip.places[0], trip.places[1], "driving")
                    segment = result.daily_plans[0].transport_segments[0]
                    self.assertEqual(segment.mode, "驾车" if mode.strip().lower() in ("打车", "出租车", "taxi") else mode)
                    self.assertEqual(segment.route, route)
                    self.assertEqual(segment.estimated_minutes, 2 if route.status == "ok" else None)
                    if route.status == "failed":
                        self.assertEqual(segment.route.parts, [])
                        self.assertIsNone(segment.route.distance_meters)
                        self.assertIsNone(segment.route.duration_seconds)

    def test_edit_taxi_alias_reuses_success_or_failure_without_query(self):
        day = self.trip.daily_plans[0]
        driving = replace(self.route, parts=[replace(self.route.parts[0], mode="driving")])
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at,
                               failure_reason="不支持的交通方式，未查询路线")
        for route, minutes in ((driving, 2), (failed, None)):
            with self.subTest(status=route.status):
                original = replace(self.trip, daily_plans=[replace(day, transport_segments=[
                    replace(day.transport_segments[0], mode="打车", route=route, estimated_minutes=minutes)])])
                edited = replace(self.trip, daily_plans=[replace(day, transport_segments=[
                    replace(day.transport_segments[0], mode=" TAXI ", estimated_minutes=99)])])
                with patch("core.trip_routes.query_amap_route") as query:
                    result = refresh_edited_day_routes(original, edited, 1)
                query.assert_not_called()
                segment = result.daily_plans[0].transport_segments[0]
                self.assertEqual((segment.mode, segment.route, segment.estimated_minutes),
                                 ("驾车", route, minutes))

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
        for mode in ("步行", "自驾", "打车", "公交", "火车"):
            with self.subTest(mode=mode):
                incoming = replace(day, transport_segments=[replace(
                    day.transport_segments[0], mode=mode, route=self.route, estimated_minutes=2)])
                failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="超时")
                with patch("core.trip_routes.query_amap_route", return_value=failed) as query:
                    result = refresh_edited_day_routes(self.trip, replace(self.trip, daily_plans=[incoming]), 1)
                self.assertEqual(query.call_count, 1)
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

    def test_bounded_transit_fallbacks_and_thresholds(self):
        day = self.trip.daily_plans[0]
        trip = replace(self.trip, request=replace(self.trip.request, preferences=[]), places=[replace(p, citycode="010") for p in self.trip.places],
                       daily_plans=[replace(day, transport_segments=[replace(day.transport_segments[0], mode="公交")])])
        no_route = RouteSnapshot("failed", "amap", self.trip.generated_at,
                                 failure_reason="无方案", failure_kind="no_route")
        blocked = replace(no_route, failure_kind="blocked")
        driving = replace(self.route, parts=[replace(self.route.parts[0], mode="driving")])
        for distance, responses, modes, actual in (
            (800, [replace(self.route, distance_meters=1200, duration_seconds=1200)], ["walking"], "步行"),
            (800, [replace(self.route, distance_meters=1201), no_route, driving], ["walking", "transit", "driving"], "驾车"),
            (800, [replace(self.route, duration_seconds=1201), no_route, no_route], ["walking", "transit", "driving"], "公共交通"),
            (801, [no_route, driving], ["transit", "driving"], "驾车"),
            (800, [blocked], ["walking"], "公共交通"),
            (801, [blocked], ["transit"], "公共交通"),
            (801, [replace(no_route, failure_kind="unavailable")], ["transit"], "公共交通"),
        ):
            with self.subTest(distance=distance, modes=modes), patch("core.trip_routes._straight_distance", return_value=distance), patch("core.trip_routes.query_amap_route", side_effect=responses) as query:
                result = enrich_trip_routes(trip)
                segment = result.daily_plans[0].transport_segments[0]
                self.assertEqual([call.args[2] for call in query.call_args_list], modes)
                self.assertEqual(segment.mode, actual)
                self.assertLessEqual(query.call_count, 3)
                if responses[-1].status == "failed":
                    self.assertIsNone(segment.estimated_minutes)
                with TemporaryDirectory() as directory:
                    db = Path(directory) / "trips.db"
                    save_itinerary("test", result, db)
                    self.assertEqual(load_itinerary("test", db), result)

    def test_explicit_road_preferences_do_not_fallback_even_when_near(self):
        day = self.trip.daily_plans[0]
        for mode, query_mode in (("自驾", "driving"), ("打车", "driving"), ("步行", "walking")):
            trip = replace(self.trip, request=replace(self.trip.request, preferences=[mode]), daily_plans=[replace(day, transport_segments=[replace(day.transport_segments[0], mode="公交")])])
            failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="无方案", failure_kind="no_route")
            with self.subTest(mode=mode), patch("core.trip_routes._straight_distance", return_value=1), patch("core.trip_routes.query_amap_route", return_value=failed) as query:
                result = enrich_trip_routes(trip)
                query.assert_called_once_with(trip.places[0], trip.places[1], query_mode)
                self.assertEqual(result.daily_plans[0].transport_segments[0].mode, "步行" if query_mode == "walking" else "驾车")

    def test_default_policy_ignores_model_mode_in_all_query_entries(self):
        day = self.trip.daily_plans[0]
        transit = replace(self.route, parts=[replace(self.route.parts[0], mode="transit")])
        for preferences in ([], ["美食"], ["不自驾"], ["自驾游"], ["步行或自驾"], ["自驾", "地铁"]):
            for model_mode in ("驾车", "自驾", "步行", "打车约10分钟", "火车"):
                for distance, expected, snapshot in ((800, "walking", self.route), (801, "transit", transit)):
                    with self.subTest(preferences=preferences, model_mode=model_mode, distance=distance):
                        trip = replace(self.trip, request=replace(self.trip.request, preferences=preferences),
                            places=[replace(p, citycode="010") for p in self.trip.places],
                            daily_plans=[replace(day, transport_segments=[replace(day.transport_segments[0], mode=model_mode)])])
                        for run in (enrich_trip_routes, complete_missing_routes,
                                    lambda value: refresh_edited_day_routes(value, value, 1)):
                            with patch("core.trip_routes._straight_distance", return_value=distance), patch(
                                    "core.trip_routes.query_amap_route", return_value=snapshot) as query:
                                segment = run(trip).daily_plans[0].transport_segments[0]
                            self.assertEqual(query.call_count, 1)
                            self.assertEqual(query.call_args.args[2], expected)
                            self.assertEqual(segment.mode, "步行" if expected == "walking" else "公共交通")
                            self.assertEqual(segment.route, snapshot)

    def test_explicit_preference_reaches_edit_and_completion(self):
        for preference, expected in ((" 自驾 ", "driving"), (" TAXI ", "driving"),
                                     ("步行", "walking"), ("地铁", "transit")):
            trip = replace(self.trip, request=replace(self.trip.request, preferences=[preference]),
                           places=[replace(p, citycode="010") for p in self.trip.places])
            for run in (enrich_trip_routes, complete_missing_routes,
                        lambda value: refresh_edited_day_routes(value, value, 1)):
                with self.subTest(preference=preference), patch(
                        "core.trip_routes._straight_distance", return_value=801), patch(
                        "core.trip_routes.query_amap_route", return_value=self.route) as query:
                    segment = run(trip).daily_plans[0].transport_segments[0]
                self.assertEqual(query.call_count, 1)
                self.assertEqual(query.call_args.args[2], expected)
                self.assertEqual(segment.mode, {"driving": "驾车", "walking": "步行", "transit": "公共交通"}[expected])

    def test_default_completion_keeps_successful_driving_snapshot(self):
        day = self.trip.daily_plans[0]
        segment = replace(day.transport_segments[0], mode="驾车", route=self.route, estimated_minutes=2)
        trip = replace(self.trip, request=replace(self.trip.request, preferences=[]),
                       daily_plans=[replace(day, transport_segments=[segment])])
        with patch("core.trip_routes.query_amap_route") as query:
            result = complete_missing_routes(trip)
        query.assert_not_called()
        self.assertIs(result.daily_plans[0].transport_segments[0], segment)
