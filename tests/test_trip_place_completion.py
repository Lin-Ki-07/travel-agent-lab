import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi import HTTPException
import api
from core.trip_models import RoutePart, RouteSnapshot
from core.trip_place_completion import complete_endpoint_citycodes
from core.trip_store import (save_itinerary, load_itinerary, update_itinerary,
                             delete_itinerary, update_itinerary_if_unchanged)
import test_trip_persistence_edit as fixtures


class EndpointCitycodeTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.trip, self.db = fixture.trip, fixture.db
        self.route = RouteSnapshot("ok", "amap", self.trip.generated_at, 100, 61,
                                   [RoutePart("walking", [[120, 30], [120.1, 30.1]])])

    def call_endpoint(self, query):
        with patch("api.load_itinerary", side_effect=lambda pid: load_itinerary(pid, self.db)), patch(
                "api.update_itinerary_if_unchanged", side_effect=lambda pid, value, fp:
                update_itinerary_if_unchanged(pid, value, fp, self.db)), patch(
                "core.trip_place_completion.query_amap_citycode", side_effect=query), patch(
                "core.trip_routes.query_amap_route", side_effect=AssertionError("No route queries")):
            return api.complete_plan_citycodes("test")

    def test_selects_only_missing_amap_endpoints_and_deduplicates_across_days(self):
        from datetime import timedelta
        day = self.trip.daily_plans[0]
        tomorrow = day.plan_date + timedelta(days=1)
        second = replace(day, day_number=2, plan_date=tomorrow,
                         weather=replace(day.weather, forecast_date=tomorrow))
        unused = replace(self.trip.places[0], place_id="UNUSED")
        for other in (replace(self.trip.places[1], citycode="010"),
                      replace(self.trip.places[1], source="other")):
            with self.subTest(other=other):
                trip = replace(self.trip, request=replace(self.trip.request, days=2),
                               places=[self.trip.places[0], other, unused], daily_plans=[day, second])
                with patch("core.trip_place_completion.query_amap_citycode", return_value="0532") as query:
                    updated, count, missing = complete_endpoint_citycodes(trip)
                query.assert_called_once_with("P1")
                self.assertEqual(count, 1)
                self.assertEqual(missing, int(other.citycode is None))
                self.assertEqual(updated.places[0], replace(trip.places[0], citycode="0532"))
                self.assertIs(updated.places[1], other)
                self.assertIs(updated.places[2], unused)
                self.assertEqual(updated.daily_plans, trip.daily_plans)

    def test_endpoint_persists_partial_result_and_preserves_all_route_facts(self):
        for snapshot in (None, self.route, RouteSnapshot("failed", "amap", self.trip.generated_at,
                                                       failure_reason="旧失败")):
            with self.subTest(snapshot=snapshot):
                day = self.trip.daily_plans[0]
                trip = replace(self.trip, daily_plans=[replace(day, transport_segments=[replace(
                    day.transport_segments[0], route=snapshot,
                    estimated_minutes=2 if snapshot == self.route else None)])])
                delete_itinerary("test", self.db)
                save_itinerary("test", trip, self.db)
                response = self.call_endpoint(lambda pid: "0532" if pid == "P1" else None)
                expected = replace(trip, places=[replace(trip.places[0], citycode="0532"), trip.places[1]])
                self.assertEqual(load_itinerary("test", self.db), expected)
                self.assertEqual((response["completed_count"], response["missing_count"]), (1, 1))

    def test_fault_stops_remaining_queries_and_does_not_save_partial_results(self):
        third = replace(self.trip.places[0], place_id="P3")
        # Add a third endpoint, to prove the failure stops subsequent lookups.
        from core.trip_models import Activity, TransportSegment
        from datetime import time
        day = self.trip.daily_plans[0]
        day = replace(day, activities=[*day.activities, Activity("P3", "第三站", time(13), time(14))],
                      transport_segments=[*day.transport_segments, TransportSegment("P2", "P3", "步行")])
        trip = replace(self.trip, places=[*self.trip.places, third], daily_plans=[day])
        for error in (RuntimeError("secret"), ValueError("secret")):
            with self.subTest(error=error):
                delete_itinerary("test", self.db)
                save_itinerary("test", trip, self.db)
                seen = []
                def query(pid):
                    seen.append(pid)
                    if pid == "P2":
                        raise error
                    return "010"
                with self.assertRaises(HTTPException) as caught:
                    self.call_endpoint(query)
                self.assertEqual(caught.exception.status_code, 502)
                self.assertNotIn("secret", caught.exception.detail)
                self.assertEqual(seen, ["P1", "P2"])
                self.assertEqual(load_itinerary("test", self.db), trip)

    def test_concurrent_edit_or_delete_is_not_overwritten(self):
        concurrent = replace(self.trip, web_evidence="并发编辑")
        for deleted in (False, True):
            with self.subTest(deleted=deleted):
                delete_itinerary("test", self.db)
                save_itinerary("test", self.trip, self.db)
                def query(pid):
                    if deleted:
                        delete_itinerary("test", self.db)
                    else:
                        update_itinerary("test", concurrent, self.db)
                    return "010"
                with self.assertRaises(HTTPException) as caught:
                    self.call_endpoint(query)
                self.assertEqual(caught.exception.status_code, 409)
                self.assertEqual(load_itinerary("test", self.db), None if deleted else concurrent)

    def test_missing_or_unsaved_id_does_not_query_or_save(self):
        with patch("api.load_itinerary", return_value=None), patch.dict(
                api.generated_plans, {"unsaved": self.trip}), patch(
                "core.trip_place_completion.query_amap_citycode") as query, patch(
                "api.update_itinerary_if_unchanged") as save:
            for pid in ("missing", "unsaved"):
                with self.subTest(pid=pid), self.assertRaises(HTTPException) as caught:
                    api.complete_plan_citycodes(pid)
                self.assertEqual(caught.exception.status_code, 404)
            query.assert_not_called()
            save.assert_not_called()

    def test_no_endpoints_or_all_codes_present_make_no_queries(self):
        day = self.trip.daily_plans[0]
        single = replace(self.trip, daily_plans=[replace(day, activities=day.activities[:1], transport_segments=[])])
        coded = replace(self.trip, places=[replace(p, citycode="010") for p in self.trip.places])
        for trip in (single, coded):
            with self.subTest(trip=trip), patch("core.trip_place_completion.query_amap_citycode") as query:
                result, completed, missing = complete_endpoint_citycodes(trip)
            query.assert_not_called()
            self.assertEqual(result, trip)
            self.assertEqual((completed, missing), (0, 0))
