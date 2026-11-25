import json
import unittest
from dataclasses import replace
from datetime import time
from unittest.mock import patch

from fastapi import HTTPException

import api
from core.trip_models import Activity, Place, TransportSegment
from tests.test_chat_service import FakeLLM, sample_itinerary


class EditDraftServiceTests(unittest.TestCase):
    def setUp(self):
        trip = sample_itinerary()
        day = replace(trip.daily_plans[0], activities=[
            Activity("P1", "上午游览", time(9), time(10)),
            Activity("P2", "下午游览", time(11), time(12)),
        ], transport_segments=[TransportSegment("P1", "P2", "步行")])
        self.trip = replace(trip, daily_plans=[day], places=[
            *trip.places,
            Place("P2", "九峰公园", "地址二", 28.1, 121.1, "amap", trip.generated_at),
            Place("P3", "府城", "地址三", 28.2, 121.2, "amap", trip.generated_at),
        ])
        self.request = {"day_number": 1, "activity_index": 0, "original_place_id": "P1", "candidate_place_id": "P3"}

    def test_valid_draft_is_read_only_and_preserves_other_activity(self):
        llm = FakeLLM(json.dumps({"description": "游览府城", "incoming_mode": None, "outgoing_mode": "公交"}, ensure_ascii=False))
        with (
            patch("api.load_itinerary", return_value=self.trip),
            patch("api.create_llm", return_value=llm),
            patch("api.update_itinerary") as update,
            patch("api.save_itinerary") as save,
        ):
            response = api.create_edit_draft("plan-1", self.request)
        self.assertEqual(response["kind"], "edit_draft")
        self.assertEqual([item["place_id"] for item in response["draft"]["activities"]], ["P3", "P2"])
        self.assertEqual(response["draft"]["transport_segments"][0]["mode"], "公交")
        self.assertEqual(self.trip.daily_plans[0].activities[0].place_id, "P1")
        update.assert_not_called()
        save.assert_not_called()

    def test_invalid_target_or_candidate_rejected_before_model(self):
        for changes in ({"original_place_id": "wrong"}, {"candidate_place_id": "missing"}, {"candidate_place_id": "P2"}):
            with self.subTest(changes=changes), patch("api.load_itinerary", return_value=self.trip), patch("api.create_llm", return_value=object()) as create_llm:
                with self.assertRaises(HTTPException) as caught:
                    api.create_edit_draft("plan-1", {**self.request, **changes})
                self.assertEqual(caught.exception.status_code, 422)
                create_llm.assert_not_called()

    def test_bad_model_output_rejected_without_write(self):
        with (
            patch("api.load_itinerary", return_value=self.trip),
            patch("api.create_llm", return_value=FakeLLM("not json")),
            patch("api.update_itinerary") as update,
        ):
            with self.assertRaises(HTTPException) as caught:
                api.create_edit_draft("plan-1", self.request)
        self.assertEqual(caught.exception.status_code, 502)
        update.assert_not_called()

    def test_missing_plan_returns_404(self):
        with patch("api.load_itinerary", return_value=None), patch.dict(api.generated_plans, {}, clear=True):
            with self.assertRaises(HTTPException) as caught:
                api.create_edit_draft("missing", self.request)
        self.assertEqual(caught.exception.status_code, 404)
