import json
import sqlite3
import unittest
import requests
from dataclasses import replace
from unittest.mock import patch

from core.trip_store import load_itinerary, save_itinerary
from tools.amap_place_tool import search_amap_places, query_amap_citycode, AMAP_PLACE_DETAIL_URL
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


    def test_detail_queries_exact_id_once_and_preserves_code(self):
        for code in ("010", "0532", None, "", [], 532, "０１０", " 010 "):
            with self.subTest(code=code), patch("tools.amap_place_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "pois": [
                    {"id": "B001", "citycode": code, "adcode": "110000"}]}
                result = query_amap_citycode(" B001 ", api_key="test-key")
                self.assertEqual(result, code if code in ("010", "0532") else None)
                get.assert_called_once_with(AMAP_PLACE_DETAIL_URL,
                    params={"key": "test-key", "id": "B001", "output": "JSON"}, timeout=(5, 10))

    def test_detail_no_result_or_missing_code_is_not_inferred(self):
        for pois in ([], [{"id": "B001", "adcode": "110000", "name": "北京", "location": "116,40"}]):
            with self.subTest(pois=pois), patch("tools.amap_place_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "pois": pois}
                self.assertIsNone(query_amap_citycode("B001", api_key="test-key"))
                get.assert_called_once()

    def test_detail_rejects_mismatched_or_malformed_response(self):
        cases = [None, [], "private-response", {}, {"status": "1"},
                 {"status": "1", "pois": {}}, {"status": "1", "pois": [None]},
                 {"status": "1", "pois": [{"id": "OTHER", "citycode": "010"}]},
                 {"status": "1", "pois": [{"id": "B001"}, {"id": "B001"}]}]
        for code in ("10001", "10002", "10003", "10004", "40000"):
            cases.append({"status": "0", "infocode": code, "info": "private-response"})
        for data in cases:
            with self.subTest(data=data), patch("tools.amap_place_tool.requests.get") as get:
                get.return_value.json.return_value = data
                with self.assertRaises(RuntimeError) as caught:
                    query_amap_citycode("B001", api_key="test-key")
                self.assertNotIn("private-response", str(caught.exception))
                self.assertNotIn("test-key", str(caught.exception))
                get.assert_called_once()

    def test_detail_transport_errors_do_not_retry_or_expose_secrets(self):
        for error in (requests.Timeout("private-url?key=test-key"),
                      requests.HTTPError("private-response"), requests.ConnectionError("test-key"),
                      ValueError("private-response")):
            with self.subTest(error=error), patch("tools.amap_place_tool.requests.get") as get:
                if isinstance(error, ValueError):
                    get.return_value.json.side_effect = error
                else:
                    get.side_effect = error
                with self.assertRaises(RuntimeError) as caught:
                    query_amap_citycode("B001", api_key="test-key")
                self.assertNotIn("test-key", str(caught.exception))
                self.assertNotIn("private", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)
                get.assert_called_once()

    def test_detail_invalid_input_or_missing_key_never_queries(self):
        with patch.dict("os.environ", {}, clear=True), patch("tools.amap_place_tool.requests.get") as get:
            for pid in (None, "", " ", "B001|B002", "B001,B002", "中文", "B 001"):
                with self.subTest(pid=pid), self.assertRaises(ValueError):
                    query_amap_citycode(pid, api_key="test-key")
            with self.assertRaisesRegex(ValueError, "AMAP_API_KEY"):
                query_amap_citycode("B001")
            get.assert_not_called()
