import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import asdict, replace
from datetime import time
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

import api
from core.trip_models import Activity, Place, RoutePart, RouteSnapshot, TransportSegment
from core.trip_store import load_itinerary, save_itinerary, update_itinerary, update_itinerary_if_unchanged
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
        llm = FakeLLM(json.dumps({"description": "游览府城"}, ensure_ascii=False))
        with (
            patch("api.load_itinerary", return_value=self.trip),
            patch("api.create_llm", return_value=llm),
            patch("api.update_itinerary") as update,
            patch("api.save_itinerary") as save,
            patch("core.trip_routes.query_amap_route") as query,
        ):
            response = api.create_edit_draft("plan-1", self.request)
        self.assertEqual(response["kind"], "edit_draft")
        self.assertEqual([item["place_id"] for item in response["draft"]["activities"]], ["P3", "P2"])
        self.assertEqual(response["draft"]["transport_segments"][0]["mode"], "步行")
        self.assertEqual(self.trip.daily_plans[0].activities[0].place_id, "P1")
        update.assert_not_called()
        save.assert_not_called()
        query.assert_not_called()

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

    def test_confirm_saves_and_rejects_stale_or_tampered_drafts(self):
        llm = FakeLLM(json.dumps({"description": "游览府城"}, ensure_ascii=False))
        with TemporaryDirectory() as directory:
            db = Path(directory) / "trips.db"
            save_itinerary("plan-1", self.trip, db)
            with (
                patch("api.load_itinerary", side_effect=lambda plan_id: load_itinerary(plan_id, db)),
                patch("api.create_llm", return_value=llm),
                patch("core.trip_routes.query_amap_route", return_value=RouteSnapshot(
                    "failed", "amap", self.trip.generated_at, failure_reason="模拟超时")) as query,
                patch("core.edit_draft_service.update_itinerary_if_unchanged", side_effect=lambda plan_id, trip, fingerprint: update_itinerary_if_unchanged(plan_id, trip, fingerprint, db)),
            ):
                draft = api.create_edit_draft("plan-1", self.request)["draft"]
                self.assertEqual(load_itinerary("plan-1", db), self.trip)
                tampered = {**draft, "activities": [{**draft["activities"][0], "start_time": "08:00"}, *draft["activities"][1:]]}
                with self.assertRaises(HTTPException) as caught:
                    api.confirm_plan_edit_draft("plan-1", tampered)
                self.assertEqual(caught.exception.status_code, 422)
                self.assertEqual(load_itinerary("plan-1", db), self.trip)
                query.assert_not_called()
                result = api.confirm_plan_edit_draft("plan-1", draft)
                query.assert_called_once()
                saved_segment = load_itinerary("plan-1", db).daily_plans[0].transport_segments[0]
                self.assertEqual(saved_segment.route.failure_reason, "模拟超时")
                self.assertIsNone(saved_segment.estimated_minutes)
                self.assertEqual(result["itinerary"]["daily_plans"][0]["activities"][0]["place_id"], "P3")
                self.assertEqual(result["map_days"][0]["stops"][0]["place_id"], "P3")
                self.assertEqual(load_itinerary("plan-1", db).daily_plans[0].activities[0].place_id, "P3")
                with self.assertRaises(HTTPException) as stale:
                    api.confirm_plan_edit_draft("plan-1", draft)
                self.assertEqual(stale.exception.status_code, 422)
                query.assert_called_once()

    def test_confirm_rejects_concurrent_change_during_route_query(self):
        with TemporaryDirectory() as directory:
            db = Path(directory) / "trips.db"
            save_itinerary("plan-1", self.trip, db)
            concurrent = replace(self.trip, web_evidence="并发更新的资料")

            def query_route(*args):
                self.assertTrue(update_itinerary("plan-1", concurrent, db))
                return RouteSnapshot("failed", "amap", self.trip.generated_at, failure_reason="模拟超时")

            with (
                patch("api.load_itinerary", side_effect=lambda plan_id: load_itinerary(plan_id, db)),
                patch("api.create_llm", return_value=FakeLLM('{"description":"新活动"}')),
                patch("core.trip_routes.query_amap_route", side_effect=query_route) as query,
                patch("core.edit_draft_service.update_itinerary_if_unchanged",
                      side_effect=lambda plan_id, trip, fingerprint: update_itinerary_if_unchanged(plan_id, trip, fingerprint, db)),
            ):
                draft = api.create_edit_draft("plan-1", self.request)["draft"]
                query.assert_not_called()
                with self.assertRaises(HTTPException) as caught:
                    api.confirm_plan_edit_draft("plan-1", draft)
                self.assertEqual(caught.exception.status_code, 422)
                self.assertEqual(load_itinerary("plan-1", db), concurrent)

    def test_day_save_updates_routes_and_removal_reuses_remaining_route(self):
        route = RouteSnapshot("ok", "amap", self.trip.generated_at, 100, 61,
                              [RoutePart("walking", [[121, 28], [121.1, 28.1]])])
        day = self.trip.daily_plans[0]
        day = replace(day, activities=[*day.activities, Activity("P3", "第三站", time(13), time(14))],
                      transport_segments=[TransportSegment("P1", "P2", "步行", 2, route),
                                          TransportSegment("P2", "P3", "步行", 2, route)])
        trip = replace(self.trip, daily_plans=[day])
        with TemporaryDirectory() as directory:
            db = Path(directory) / "trips.db"
            with (
                patch("api.load_itinerary", side_effect=lambda plan_id: load_itinerary(plan_id, db)),
                patch("api.update_itinerary", side_effect=lambda plan_id, edited: update_itinerary(plan_id, edited, db)),
                patch("core.trip_routes.query_amap_route", return_value=route) as query,
            ):
                for removed_index, expected_queries in ((0, 0), (1, 1)):
                    with self.subTest(removed_index=removed_index):
                        save_itinerary("plan-1", trip, db)
                        activities = [a for i, a in enumerate(day.activities) if i != removed_index]
                        body = jsonable_encoder({"activities": [asdict(a) for a in activities],
                            "transport_segments": [{"from_place_id": activities[0].place_id,
                                "to_place_id": activities[1].place_id, "mode": "步行", "estimated_minutes": 99}]})
                        query.reset_mock()
                        result = api.update_plan_day("plan-1", 1, body)
                        self.assertEqual(query.call_count, expected_queries)
                        saved = load_itinerary("plan-1", db)
                        self.assertEqual(saved.daily_plans[0].transport_segments[0].estimated_minutes, 2)
                        self.assertEqual(result["itinerary"]["daily_plans"][0]["transport_segments"][0]["route"]["status"], "ok")
