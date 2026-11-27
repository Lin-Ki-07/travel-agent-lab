import json
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.encoders import jsonable_encoder

from core.trip_models import RoutePart, RouteSnapshot, TransportSegment, parse_route_snapshot
from core.itinerary_validator import parse_itinerary
from core.trip_store import save_itinerary, load_itinerary
import test_trip_persistence_edit as persistence_fixtures


class RouteSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        self.route = RouteSnapshot("ok", "amap", self.now, 100, 61,
                                   [RoutePart("walking", [[120, 30], [120.1, 30.1]])])

    def test_success_and_failure_round_trip(self):
        fixture = persistence_fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for route, minutes in ((self.route, 2), (RouteSnapshot(
                "failed", "amap", self.now, failure_reason="无路线"), None)):
            with self.subTest(status=route.status), TemporaryDirectory() as directory:
                segment = TransportSegment("P1", "P2", "步行", minutes, route)
                trip = replace(fixture.trip, daily_plans=[replace(
                    fixture.trip.daily_plans[0], transport_segments=[segment])])
                db = Path(directory) / "test.db"
                save_itinerary("test", trip, db)
                self.assertEqual(load_itinerary("test", db), trip)

    def test_invalid_snapshot_fields(self):
        raw = jsonable_encoder(asdict(self.route))
        for change in ({"distance_meters": -1}, {"duration_seconds": True},
                       {"duration_seconds": 0}, {"queried_at": "2026-11-26T00:00:00"},
                       {"status": "unknown"}, {"parts": []},
                       {"failure_reason": "失败"},
                       {"parts": [{"mode": "walking", "positions": [[181, 30], [120, 30]]}]},
                       {"parts": [{"mode": "walking", "positions": [[float('nan'), 30], [120, 30]]}]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_route_snapshot({**raw, **change})
        with self.assertRaises(ValueError):
            RouteSnapshot("failed", "amap", self.now)
        with self.assertRaises(ValueError):
            RouteSnapshot("failed", "amap", self.now, distance_meters=1, failure_reason="失败")

    def test_minutes_must_match_snapshot(self):
        with self.assertRaises(ValueError):
            TransportSegment("P1", "P2", "步行", 1, self.route)

    def test_model_output_cannot_supply_route_facts(self):
        fixture = persistence_fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        raw = jsonable_encoder(asdict(fixture.trip))
        raw["daily_plans"][0]["transport_segments"][0]["route"] = jsonable_encoder(asdict(self.route))
        parsed = parse_itinerary(json.dumps(raw), fixture.trip.request, fixture.trip.places,
                                 [fixture.trip.daily_plans[0].weather])
        self.assertIsNone(parsed.daily_plans[0].transport_segments[0].route)
