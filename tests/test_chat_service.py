import json
import unittest
from dataclasses import replace
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
    def test_tool_routing_keeps_edit_requests_on_conversation_path(self):
        from core.chat_service import needs_travel_tools

        for text in ("台州现在天气如何？", "查一下景区最新开放时间", "查询门票价格"):
            with self.subTest(text=text):
                self.assertTrue(needs_travel_tools(text))
        for text in ("第一天去哪？", "换掉明天天气不好的景点", "查一下路线", "调整行程，查一下门票"):
            with self.subTest(text=text):
                self.assertFalse(needs_travel_tools(text))

    def test_tool_answer_uses_fresh_agent_and_existing_contract(self):
        class FakeToolAgent:
            def __init__(self):
                self.prompts = []

            def run(self, prompt):
                self.prompts.append(prompt)
                return "模拟工具结果：台州当前天气晴。"

        agents = []

        def new_agent(_llm):
            agent = FakeToolAgent()
            agents.append(agent)
            return agent

        itinerary = sample_itinerary()
        with (
            patch("api.load_itinerary", return_value=itinerary),
            patch("api.create_llm", return_value=object()),
            patch("api.create_web_travel_agent", side_effect=new_agent),
            patch("api.update_itinerary") as update,
        ):
            first = api.chat({"text": "台州现在天气如何？", "plan_id": "saved-plan", "history": [{"role": "user", "content": "准备去台州"}]})
            second = api.chat({"text": "台州现在天气如何？", "plan_id": "saved-plan"})
        self.assertEqual(first, {"kind": "answer", "message": "模拟工具结果：台州当前天气晴。"})
        self.assertEqual(second["kind"], "answer")
        self.assertIsNot(agents[0], agents[1])
        self.assertIn("合胜广场", agents[0].prompts[0])
        self.assertIn("准备去台州", agents[0].prompts[0])
        self.assertNotIn("准备去台州", agents[1].prompts[0])
        update.assert_not_called()

    def test_tool_failure_returns_502(self):
        class FailingToolAgent:
            def run(self, _prompt):
                raise LLMError("模拟工具模型失败")

        with (
            patch("api.create_llm", return_value=object()),
            patch("api.create_web_travel_agent", return_value=FailingToolAgent()),
        ):
            with self.assertRaises(HTTPException) as caught:
                api.chat({"text": "台州现在天气如何？"})
        self.assertEqual(caught.exception.status_code, 502)

    def test_summary_numbers_repeated_places_and_read_only_target(self):
        itinerary = sample_itinerary()
        day_one = replace(itinerary.daily_plans[0], activities=[
            Activity("P1", "上午游览", time(9), time(10)),
            Activity("P2", "下午游览", time(14), time(15)),
        ])
        day_two = replace(
            day_one, day_number=2, plan_date=date(2026, 11, 25),
            weather=replace(day_one.weather, forecast_date=date(2026, 11, 25)),
            activities=[Activity("P1", "再次游览", time(9), time(10))],
        )
        itinerary = replace(
            itinerary,
            request=replace(itinerary.request, days=2),
            places=[*itinerary.places, Place("P2", "九峰公园", "示例地址", 28.1, 121.1, "amap", itinerary.generated_at)],
            daily_plans=[day_one, day_two],
        )
        output = json.dumps({
            "kind": "edit_target", "message": "已定位目标，尚未修改行程",
            "target": {"day_number": 2, "activity_index": 0, "place_id": "P1"},
        }, ensure_ascii=False)
        fake = FakeLLM(output)
        with (
            patch("api.load_itinerary", return_value=itinerary),
            patch("api.create_llm", return_value=fake),
            patch("api.update_itinerary") as update,
        ):
            response = api.chat({"text": "把第二天第一项换掉", "plan_id": "saved-plan"})
        self.assertEqual(response["kind"], "edit_target")
        self.assertIn("第 2 天", fake.messages[-2].content)
        self.assertIn("activity_index=0，place_id=P1", fake.messages[-2].content)
        self.assertEqual(itinerary.daily_plans[1].activities[0].place_id, "P1")
        update.assert_not_called()

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

    def test_edit_target_must_match_current_itinerary(self):
        itinerary = sample_itinerary()
        for day_number, activity_index, place_id, expected in (
            (1, 0, "P1", "edit_target"),
            (1, 0, "missing", "clarify"),
            (2, 0, "P1", "clarify"),
            (1, 4, "P1", "clarify"),
        ):
            output = json.dumps({
                "kind": "edit_target", "message": "已定位，尚未修改行程",
                "target": {"day_number": day_number, "activity_index": activity_index, "place_id": place_id},
            }, ensure_ascii=False)
            with self.subTest(target=(day_number, activity_index, place_id)):
                with (
                    patch("api.load_itinerary", return_value=itinerary),
                    patch("api.create_llm", return_value=FakeLLM(output)),
                    patch("api.update_itinerary") as update,
                ):
                    response = api.chat({"text": "换掉这项", "plan_id": "saved-plan"})
                self.assertEqual(response["kind"], expected)
                update.assert_not_called()
