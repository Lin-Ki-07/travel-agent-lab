import unittest

from pydantic import ValidationError

from core.chat_contract import ChatRequest, chat_response_adapter


class ChatContractTests(unittest.TestCase):
    def test_request_and_three_response_kinds(self):
        request = ChatRequest.model_validate({
            "text": "把合胜换成九峰公园",
            "plan_id": "saved-plan",
            "history": [{"role": "user", "content": "想调整第一天"}],
        })
        self.assertEqual(request.plan_id, "saved-plan")

        for kind in ("answer", "clarify"):
            response = chat_response_adapter.validate_python({"kind": kind, "message": "示例回复"})
            self.assertEqual(response.kind, kind)

        response = chat_response_adapter.validate_python({
            "kind": "edit_draft",
            "message": "请确认草案",
            "draft": {
                "plan_id": "saved-plan", "day_number": 1, "activity_index": 2,
                "original_place_id": "P1", "candidate_place_id": "P2",
                "activities": [{"place_id": "P2", "description": "游览", "start_time": "09:00", "end_time": "10:00"}],
                "transport_segments": [],
            },
        })
        self.assertEqual(response.draft.candidate_place_id, "P2")

    def test_invalid_kind_and_missing_draft_are_rejected(self):
        for payload in ({"kind": "save", "message": "保存"}, {"kind": "edit_draft", "message": "草案"}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                chat_response_adapter.validate_python(payload)

    def test_draft_cannot_reuse_original_place(self):
        with self.assertRaises(ValidationError):
            chat_response_adapter.validate_python({
                "kind": "edit_draft", "message": "草案",
                "draft": {
                    "plan_id": "saved-plan", "day_number": 1, "activity_index": 0,
                    "original_place_id": "P1", "candidate_place_id": "P1",
                    "activities": [{}], "transport_segments": [],
                },
            })

    def test_request_rejects_empty_message_and_unknown_field(self):
        for payload in ({"text": ""}, {"text": "你好", "auto_save": True}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ChatRequest.model_validate(payload)
