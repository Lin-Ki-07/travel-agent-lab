import json
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from core.trip_input import parse_trip_request
from core.trip_models import Place, WeatherSnapshot
from core.trip_planner import generate_itinerary
from core.trip_sources import gather_trip_sources


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def generate(self, messages, system_prompt):
        self.calls += 1
        return next(self.responses)


class TripFlowTests(unittest.TestCase):
    def setUp(self):
        self.request = parse_trip_request({
            "destination": "杭州",
            "start_date": "2026-11-10",
            "days": "2",
        })
        now = datetime.now(timezone.utc)
        self.place = Place("P1", "示例地点", "示例地址", 30, 120, "amap", now)
        self.weather = [
            WeatherSnapshot(
                date(2026, 11, 10) + timedelta(days=offset),
                None, None, None, False, "wttr.in", now
            )
            for offset in range(2)
        ]

    def valid_json(self):
        return json.dumps({
            "daily_plans": [
                {
                    "plan_date": snapshot.forecast_date.isoformat(),
                    "activities": [{
                        "place_id": "P1",
                        "description": "参观",
                        "start_time": "09:00",
                        "end_time": "10:00",
                    }],
                    "transport_segments": [],
                    "estimated_cost_cny": None,
                    "cost_basis": None,
                }
                for snapshot in self.weather
            ],
            "estimated_total_cny": None,
        }, ensure_ascii=False)

    def test_normal_flow(self):
        with (
            patch("core.trip_sources.search_amap_places",
                  return_value=[self.place]),
            patch("core.trip_sources.get_trip_weather",
                  return_value=self.weather),
            patch("core.trip_sources.search_travel_evidence",
                  return_value="[1] 示例证据"),
        ):
            places, weather, evidence = gather_trip_sources(self.request)

        llm = FakeLLM([self.valid_json()])
        trip = generate_itinerary(
            llm, self.request, places, weather, evidence
        )
        self.assertEqual(len(trip.daily_plans), 2)
        self.assertEqual(trip.daily_plans[0].activities[0].place_id, "P1")
        self.assertEqual(llm.calls, 1)

    def test_missing_destination(self):
        with self.assertRaisesRegex(ValueError, "目的地"):
            parse_trip_request({
                "destination": "",
                "start_date": "2026-11-10",
                "days": "2",
            })

    def test_place_tool_failure(self):
        with patch(
            "core.trip_sources.search_amap_places",
            side_effect=RuntimeError("模拟超时"),
        ):
            with self.assertRaisesRegex(RuntimeError, "地点查询失败"):
                gather_trip_sources(self.request)

    def test_invalid_model_output(self):
        llm = FakeLLM(["不是 JSON", "仍不是 JSON"])
        with self.assertRaisesRegex(RuntimeError, "两次输出"):
            generate_itinerary(
                llm, self.request, [self.place], self.weather, "[1] 示例证据"
            )
        self.assertEqual(llm.calls, 2)


if __name__ == "__main__":
    unittest.main()