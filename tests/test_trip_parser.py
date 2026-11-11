import json
import unittest
from datetime import date

from core.exceptions import LLMError
from core.trip_parser import parse_trip_text


class FakeLLM:
    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def generate(self, messages, system_prompt):
        self.calls.append((messages, system_prompt))
        if self.error:
            raise self.error
        return self.reply


def fields(**overrides):
    base = {
        "destination": "杭州", "start_date": "2026-11-20", "days": "2",
        "end_date": "", "travelers": "", "budget_cny": "", "preferences": "美食",
    }
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


class ParseTripTextTests(unittest.TestCase):
    def test_parses_complete_request(self):
        llm = FakeLLM(reply=fields())
        result = parse_trip_text(llm, "我想去杭州玩两天，美食为主", today=date(2026, 11, 11))
        self.assertEqual(result["fields"]["destination"], "杭州")
        self.assertEqual(result["fields"]["days"], "2")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["issues"], [])
        self.assertIn("杭州", result["summary"])

    def test_today_is_passed_into_system_prompt(self):
        llm = FakeLLM(reply=fields())
        parse_trip_text(llm, "明天去杭州", today=date(2026, 11, 11))
        _, system_prompt = llm.calls[0]
        self.assertIn("2026-11-11", system_prompt)

    def test_fenced_json_is_accepted(self):
        llm = FakeLLM(reply="```json\n" + fields() + "\n```")
        result = parse_trip_text(llm, "杭州两天", today=date(2026, 11, 11))
        self.assertEqual(result["fields"]["destination"], "杭州")

    def test_missing_required_fields_are_reported(self):
        llm = FakeLLM(reply=fields(destination="", start_date="", days=""))
        result = parse_trip_text(llm, "想出去玩", today=date(2026, 11, 11))
        self.assertEqual(result["missing"], ["destination", "start_date", "days"])
        self.assertEqual(result["issues"], [])

    def test_days_or_end_date_satisfies_duration(self):
        llm = FakeLLM(reply=fields(days="", end_date="2026-11-21"))
        result = parse_trip_text(llm, "11 月 20 到 21 号去杭州", today=date(2026, 11, 11))
        self.assertNotIn("days", result["missing"])

    def test_invalid_values_become_issues_not_errors(self):
        llm = FakeLLM(reply=fields(start_date="2026-02-30"))
        result = parse_trip_text(llm, "杭州", today=date(2026, 11, 11))
        self.assertEqual(result["missing"], [])
        self.assertEqual(len(result["issues"]), 1)

    def test_unknown_keys_are_dropped_and_missing_keys_filled(self):
        llm = FakeLLM(reply=json.dumps({"destination": "杭州", "extra": "x"}, ensure_ascii=False))
        result = parse_trip_text(llm, "杭州", today=date(2026, 11, 11))
        self.assertNotIn("extra", result["fields"])
        self.assertEqual(result["fields"]["travelers"], "")

    def test_empty_text_is_rejected_before_model_call(self):
        llm = FakeLLM(reply=fields())
        with self.assertRaises(ValueError):
            parse_trip_text(llm, "   ", today=date(2026, 11, 11))
        self.assertEqual(llm.calls, [])

    def test_non_json_output_raises_value_error(self):
        llm = FakeLLM(reply="这不是 JSON")
        with self.assertRaises(ValueError):
            parse_trip_text(llm, "杭州", today=date(2026, 11, 11))

    def test_non_object_json_raises_value_error(self):
        llm = FakeLLM(reply="[1, 2]")
        with self.assertRaises(ValueError):
            parse_trip_text(llm, "杭州", today=date(2026, 11, 11))

    def test_model_failure_raises_runtime_error(self):
        llm = FakeLLM(error=LLMError("超时"))
        with self.assertRaises(RuntimeError):
            parse_trip_text(llm, "杭州", today=date(2026, 11, 11))


if __name__ == "__main__":
    unittest.main()
