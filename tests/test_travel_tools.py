import unittest
from unittest.mock import patch

from agents.travel_tools import create_travel_tool_registry


class TravelToolRegistryTests(unittest.TestCase):
    def test_read_only_tool_set_is_isolated_per_registry(self):
        cli = create_travel_tool_registry()
        web = create_travel_tool_registry()

        for registry in (cli, web):
            self.assertTrue(registry.has_tool("get_weather"))
            self.assertTrue(registry.has_tool("search_travel_evidence"))
            self.assertFalse(registry.has_tool("memory"))
            self.assertFalse(registry.has_tool("save_itinerary"))
            self.assertFalse(registry.has_tool("delete_itinerary"))
            self.assertIn("question: string", registry.describe())

        cli.register_function("cli_only", lambda: "ok")
        self.assertTrue(cli.has_tool("cli_only"))
        self.assertFalse(web.has_tool("cli_only"))

    def test_execute_records_mocked_weather_and_search(self):
        search_calls = []

        def fake_search(question: str) -> str:
            search_calls.append(question)
            return "模拟证据"

        with (
            patch("agents.travel_tools.search_travel_evidence", fake_search),
            patch("agents.travel_tools.WeatherTool") as weather_type,
        ):
            weather = weather_type.return_value
            weather.name = "get_weather"
            weather.description = "查询天气"
            weather.run = lambda city: f"{city}模拟天气"
            registry = create_travel_tool_registry()

        self.assertEqual(registry.execute("get_weather", city="台州"), "台州模拟天气")
        self.assertEqual(registry.execute("search_travel_evidence", question="台州景点"), "模拟证据")
        self.assertEqual(search_calls, ["台州景点"])
        self.assertEqual([record.name for record in registry.get_execution_records()], [
            "get_weather", "search_travel_evidence",
        ])
