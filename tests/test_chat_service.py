import json
import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

from fastapi import HTTPException

import api
from core.exceptions import LLMError
from core.trip_models import Activity, DailyPlan, Itinerary, Place, TripRequest, WeatherSnapshot


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.messages = None

    def generate(self, messages, system_prompt):
        self.messages = messages
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def sample_itinerary():
    now = datetime.now(timezone.utc)
    travel_date = date(2026, 11, 24)
    return Itinerary(
        request=TripRequest("台州", travel_date, 1),
        places=[Place("P1", "合胜广场", "示例地址", 28.0, 121.0, "amap", now)],
        daily_plans=[DailyPlan(
            1, travel_date,
            WeatherSnapshot(travel_date, None, None, None, False, "wttr.in", now),
            [Activity("P1", "游览", time(9), time(10))],
        )],
        estimated_total_cny=None,
        generated_at=now,
    )


class ChatServiceTests(unittest.TestCase):
    def test_answer_uses_current_itinerary_without_writing(self):
        itinerary = sample_itinerary()
        fake = FakeLLM(json.dumps({"kind": "answer", "message": "第一天有合胜广场。"}, ensure_ascii=False))
        with (
            patch("api.load_itinerary", return_value=itinerary),
            patch("api.create_llm", return_value=fake),
            patch("api.update_itinerary") as update,
            patch("api.save_itinerary") as save,
        ):
            response = api.chat({"text": "第一天去哪？", "plan_id": "saved-plan", "history": []})
        self.assertEqual(response, {"kind": "answer", "message": "第一天有合胜广场。"})
        self.assertIn("合胜广场", fake.messages[-2].content)
        update.assert_not_called()
        save.assert_not_called()

    def test_invalid_response_and_model_failure_return_502(self):
        for output in ('{"kind":"edit_draft","message":"修改"}', LLMError("模拟失败")):
            with self.subTest(output=output), patch("api.create_llm", return_value=FakeLLM(output)):
                with self.assertRaises(HTTPException) as caught:
                    api.chat({"text": "你好", "history": []})
                self.assertEqual(caught.exception.status_code, 502)

    def test_missing_plan_returns_404_without_model_call(self):
        with patch("api.load_itinerary", return_value=None), patch("api.create_llm") as create_llm:
            with self.assertRaises(HTTPException) as caught:
                api.chat({"text": "第一天去哪？", "plan_id": "missing"})
        self.assertEqual(caught.exception.status_code, 404)
        create_llm.assert_not_called()

    def test_clarify_response(self):
        fake = FakeLLM('{"kind":"clarify","message":"你想调整哪一天？"}')
        with patch("api.create_llm", return_value=fake):
            response = api.chat({"text": "想调整行程"})
        self.assertEqual(response["kind"], "clarify")
