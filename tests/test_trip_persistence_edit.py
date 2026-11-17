import unittest
from datetime import date, datetime, time, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from core.map_view import build_map_days
from core.trip_edit import edit_day
from core.trip_models import (
    Activity, DailyPlan, Itinerary, Place, TripRequest, TransportSegment,
    WeatherSnapshot,
)
from core.trip_store import (
    list_saved_plans, load_itinerary, load_preferences, save_itinerary,
    save_preferences, update_itinerary,
)


class TripPersistenceEditTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "trips.db"
        self.now = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)
        trip_date = date(2026, 11, 21)
        request = TripRequest("杭州", trip_date, 1, preferences=["美食"])
        places = [
            Place("P1", "地点一", "地址一", 30.0, 120.0, "amap", self.now),
            Place("P2", "地点二", "地址二", 30.1, 120.1, "amap", self.now),
        ]
        weather = WeatherSnapshot(
            trip_date, "晴", 10, 20, True, "wttr.in", self.now,
        )
        day = DailyPlan(
            1, trip_date, weather,
            [
                Activity("P1", "上午", time(9), time(10)),
                Activity("P2", "下午", time(11), time(12)),
            ],
            [TransportSegment("P1", "P2", "步行")],
        )
        self.trip = Itinerary(
            request, places, [day], None, self.now,
            "[1] 标题：资料\nURL：https://example.com\n文本：搜索摘要",
        )

    def test_saved_plan_survives_fresh_store_read_with_snapshots(self):
        self.assertIsNone(load_itinerary("plan-1", self.db))
        self.assertEqual(list_saved_plans(self.db), [])

        save_itinerary("plan-1", self.trip, self.db)
        restored = load_itinerary("plan-1", self.db)
        self.assertEqual(restored, self.trip)
        self.assertEqual(restored.generated_at, self.now)
        self.assertEqual(restored.places[0].queried_at, self.now)
        self.assertEqual(restored.daily_plans[0].weather.queried_at, self.now)
        self.assertEqual(restored.web_evidence, self.trip.web_evidence)
        self.assertEqual(list_saved_plans(self.db)[0]["plan_id"], "plan-1")

    def test_valid_edit_persists_and_map_follows_activity_order(self):
        save_itinerary("plan-1", self.trip, self.db)
        edited = edit_day(load_itinerary("plan-1", self.db), 1, {
            "activities": [
                {"place_id": "P2", "description": "先去二", "start_time": "09:00", "end_time": "10:00"},
                {"place_id": "P1", "description": "再去一", "start_time": "11:00", "end_time": "12:00"},
            ],
            "transport_segments": [
                {"from_place_id": "P2", "to_place_id": "P1", "mode": "步行", "estimated_minutes": None},
            ],
        })
        self.assertTrue(update_itinerary("plan-1", edited, self.db))

        restored = load_itinerary("plan-1", self.db)
        self.assertEqual(restored, edited)
        self.assertEqual(restored.web_evidence, self.trip.web_evidence)
        self.assertIsNone(restored.daily_plans[0].estimated_cost_cny)
        self.assertIsNone(restored.estimated_total_cny)
        map_day = build_map_days(restored)[0]
        self.assertEqual([stop["place_id"] for stop in map_day["stops"]], ["P2", "P1"])
        self.assertEqual(map_day["line"]["positions"], [[120.1, 30.1], [120.0, 30.0]])

    def test_invalid_edits_leave_saved_record_unchanged(self):
        save_itinerary("plan-1", self.trip, self.db)
        invalid_cases = [
            ({"activities": [
                {"place_id": "missing", "description": "不存在", "start_time": "09:00", "end_time": "10:00"},
            ], "transport_segments": []}, "未查询到的地点"),
            ({"activities": [
                {"place_id": "P1", "description": "上午", "start_time": "09:00", "end_time": "11:00"},
                {"place_id": "P2", "description": "重叠", "start_time": "10:00", "end_time": "12:00"},
            ], "transport_segments": [
                {"from_place_id": "P1", "to_place_id": "P2", "mode": "步行"},
            ]}, "时间重叠"),
            ({"activities": [
                {"place_id": "P2", "description": "先去二", "start_time": "09:00", "end_time": "10:00"},
                {"place_id": "P1", "description": "再去一", "start_time": "11:00", "end_time": "12:00"},
            ], "transport_segments": []}, "地点顺序"),
        ]
        for body, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    edit_day(load_itinerary("plan-1", self.db), 1, body)
                self.assertEqual(load_itinerary("plan-1", self.db), self.trip)

    def test_preferences_are_independent_of_saved_trip(self):
        save_itinerary("plan-1", self.trip, self.db)
        self.assertEqual(load_preferences(self.db), [])
        save_preferences(["博物馆"], self.db)
        self.assertEqual(load_preferences(self.db), ["博物馆"])
        self.assertEqual(load_itinerary("plan-1", self.db).request.preferences, ["美食"])


if __name__ == "__main__":
    unittest.main()
