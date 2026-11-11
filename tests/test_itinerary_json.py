import json
import unittest

from core.itinerary_validator import extract_json_text


class ExtractJsonTextTests(unittest.TestCase):
    def test_plain_json_unchanged(self):
        self.assertEqual(json.loads(extract_json_text('{"a": 1}')), {"a": 1})

    def test_markdown_fence_with_language(self):
        raw = '```json\n{"a": 1}\n```'
        self.assertEqual(json.loads(extract_json_text(raw)), {"a": 1})

    def test_markdown_fence_without_language(self):
        raw = '```\n{"a": 1}\n```'
        self.assertEqual(json.loads(extract_json_text(raw)), {"a": 1})

    def test_prose_around_object_is_removed(self):
        raw = '好的，结果如下：\n{"a": 1}\n希望有帮助。'
        self.assertEqual(json.loads(extract_json_text(raw)), {"a": 1})

    def test_nested_objects_are_kept_intact(self):
        raw = '```json\n{"a": {"b": [1, 2]}}\n```'
        self.assertEqual(json.loads(extract_json_text(raw)), {"a": {"b": [1, 2]}})

    def test_non_json_text_still_fails_to_parse(self):
        with self.assertRaises(json.JSONDecodeError):
            json.loads(extract_json_text("这不是 JSON"))


if __name__ == "__main__":
    unittest.main()
