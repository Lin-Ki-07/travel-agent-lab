import json
import sqlite3
import unittest
from dataclasses import replace
from unittest.mock import patch
from fastapi import HTTPException
import api
from core.trip_models import RoutePart, RouteSnapshot
from core.trip_routes import complete_missing_routes
from core.trip_store import save_itinerary, load_itinerary, update_itinerary, update_itinerary_if_unchanged
import test_trip_persistence_edit as fixtures


class RouteCompletionTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.trip, self.db = fixture.trip, fixture.db
        self.route = RouteSnapshot("ok", "amap", self.trip.generated_at, 100, 61,
                                   [RoutePart("walking", [[120, 30], [120.1, 30.1]])])

    def test_completion_queries_missing_or_failed_but_not_success(self):
        day = self.trip.daily_plans[0]
        failed = RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="旧失败")
        for snapshot in (None, failed, self.route):
            with self.subTest(snapshot=snapshot):
                segment = replace(day.transport_segments[0], route=snapshot,
                                  estimated_minutes=2 if snapshot == self.route else None)
                trip = replace(self.trip, daily_plans=[replace(day, transport_segments=[segment])])
                with patch("core.trip_routes.query_amap_route", return_value=self.route) as query:
                    result = complete_missing_routes(trip)
                self.assertEqual(query.call_count, int(snapshot != self.route))
                self.assertEqual(result.daily_plans[0].activities, day.activities)
                self.assertEqual(result.daily_plans[0].transport_segments[0].route, self.route)

    def test_endpoint_persists_legacy_json_and_rejects_concurrent_change(self):
        save_itinerary("test", self.trip, self.db)
        with sqlite3.connect(self.db) as connection:
            data = json.loads(connection.execute("SELECT itinerary_json FROM saved_plans").fetchone()[0])
            for place in data["places"]:
                del place["citycode"]
            connection.execute("UPDATE saved_plans SET itinerary_json=?", (json.dumps(data),))
        with patch("api.load_itinerary", side_effect=lambda pid: load_itinerary(pid, self.db)), patch(
            "api.update_itinerary_if_unchanged", side_effect=lambda pid, trip, fp: update_itinerary_if_unchanged(pid, trip, fp, self.db)), patch(
            "core.trip_routes.query_amap_route", return_value=self.route) as query:
            response = api.complete_plan_routes("test")
        query.assert_called_once()
        self.assertEqual(response["map_days"][0]["segments"][0]["kind"], "route_snapshot")
        self.assertEqual(load_itinerary("test", self.db).daily_plans[0].transport_segments[0].route, self.route)
        update_itinerary("test", self.trip, self.db)
        concurrent = replace(self.trip, web_evidence="并发编辑")
        def query_route(*args, **kwargs):
            update_itinerary("test", concurrent, self.db)
            return self.route
        with patch("api.load_itinerary", side_effect=lambda pid: load_itinerary(pid, self.db)), patch(
            "api.update_itinerary_if_unchanged", side_effect=lambda pid, trip, fp: update_itinerary_if_unchanged(pid, trip, fp, self.db)), patch(
            "core.trip_routes.query_amap_route", side_effect=query_route):
            with self.assertRaises(HTTPException) as caught:
                api.complete_plan_routes("test")
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(load_itinerary("test", self.db), concurrent)

    def test_unknown_plan_does_not_query(self):
        with patch("api.load_itinerary", return_value=None), patch("core.trip_routes.query_amap_route") as query:
            with self.assertRaises(HTTPException) as caught:
                api.complete_plan_routes("missing")
        self.assertEqual(caught.exception.status_code, 404)
        query.assert_not_called()
