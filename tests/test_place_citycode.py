import json
import sqlite3
import unittest
from dataclasses import replace
from unittest.mock import patch

from core.trip_store import load_itinerary, save_itinerary
from tools.amap_place_tool import search_amap_places
import test_trip_persistence_edit as fixtures


class PlaceCitycodeTests(unittest.TestCase):
    def test_poi_citycode_preserves_leading_zero_and_invalid_values_keep_place(self):
        for value in ("010", "0532", None, "", [], 532, "青岛", "０１０", " 010 "):
            with self.subTest(value=value), patch("tools.amap_place_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "pois": [{
                    "id": "P1", "name": "地点", "location": "120,30",
                    "citycode": value, "adcode": "370202",
                }]}
                places = search_amap_places("青岛", api_key="test-key")
                get.assert_called_once()
                self.assertEqual(len(places), 1)
                self.assertEqual(places[0].citycode, value if value in ("010", "0532") else None)

    def test_missing_citycode_is_not_inferred_from_adcode(self):
        with patch("tools.amap_place_tool.requests.get") as get:
            get.return_value.json.return_value = {"status": "1", "pois": [{
                "id": "P1", "name": "地点", "location": "120,30", "adcode": "370202",
            }]}
            self.assertIsNone(search_amap_places("青岛", api_key="test-key")[0].citycode)

    def test_citycode_roundtrip_and_legacy_json_without_field(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        trip = replace(fixture.trip, places=[
            replace(fixture.trip.places[0], citycode="010"), fixture.trip.places[1],
        ])
        save_itinerary("test", trip, fixture.db)
        self.assertEqual(load_itinerary("test", fixture.db), trip)
        # 仅修改临时测试库，模拟新增字段前的实际 JSON 格式。
        with sqlite3.connect(fixture.db) as connection:
            raw = connection.execute("SELECT itinerary_json FROM saved_plans").fetchone()[0]
            data = json.loads(raw)
            for place in data["places"]:
                del place["citycode"]
            connection.execute("UPDATE saved_plans SET itinerary_json = ?", (json.dumps(data),))
        restored = load_itinerary("test", fixture.db)
        self.assertEqual(restored, fixture.trip)
        self.assertTrue(all(place.citycode is None for place in restored.places))

    def test_place_rejects_invalid_citycode(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for value in ("", [], 10, "０１０", " 010 "):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "城市编码"):
                replace(fixture.trip.places[0], citycode=value)
