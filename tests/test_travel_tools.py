import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import api
from agents.react_agent import ReActAgent
from agents.travel_tools import create_travel_tool_registry, create_web_travel_agent
from core.config import AgentConfig


class TravelToolRegistryTests(unittest.TestCase):
    def test_web_chat_runs_weather_tool_and_isolates_requests(self):
        class ScriptedLLM:
            def __init__(self):
                self.calls = []

            def generate(self, messages, system_prompt):
                self.calls.append([message.content for message in messages])
                if len(self.calls) == 1:
                    return 'Thought: 查询天气\nAction: get_weather(city="台州")'
                return 'Thought: 根据工具结果回答\nAction: Finish[台州当前晴。]'

        models = []

        def new_llm():
            model = ScriptedLLM()
            models.append(model)
            return model

        with (
            patch("api.create_llm", side_effect=new_llm),
            patch("tools.weather_tool.get_weather", return_value="台州当前晴，20摄氏度") as weather,
            redirect_stdout(StringIO()),
        ):
            first = api.chat({"text": "台州现在天气如何？"})
            second = api.chat({"text": "台州现在天气如何？"})

        self.assertEqual(first, {"kind": "answer", "message": "台州当前晴。"})
        self.assertEqual(second, first)
        self.assertEqual(weather.call_count, 2)
        self.assertEqual(len(models), 2)
        for model in models:
            self.assertEqual(len(model.calls), 2)
            self.assertEqual(len(model.calls[0]), 1)
            self.assertTrue(any("台州当前晴，20摄氏度" in item for item in model.calls[1]))

    def test_web_chat_search_result_and_empty_result_are_visible_to_agent(self):
        class SearchLLM:
            def __init__(self):
                self.messages = []

            def generate(self, messages, system_prompt):
                self.messages.append([message.content for message in messages])
                if len(self.messages) == 1:
                    return 'Thought: 搜索资料\nAction: search_travel_evidence(question="台州景区最新开放时间")'
                return 'Thought: 说明已知信息\nAction: Finish[请以搜索结果为准。]'

        for result in ("[1] 标题：景区公告\nURL：https://example.com\n文本：开放时间", "搜索完成，但没有找到可引用的旅行资料。"):
            with self.subTest(result=result):
                llm = SearchLLM()
                search_calls = []

                def fake_search(question: str) -> str:
                    search_calls.append(question)
                    return result

                with (
                    patch("api.create_llm", return_value=llm),
                    patch("agents.travel_tools.search_travel_evidence", fake_search),
                    redirect_stdout(StringIO()),
                ):
                    response = api.chat({"text": "查一下台州景区最新开放时间"})
                self.assertEqual(response["kind"], "answer")
                self.assertEqual(search_calls, ["台州景区最新开放时间"])
                self.assertTrue(any(result in item for item in llm.messages[1]))

    def test_cli_react_keeps_shared_read_only_tools(self):
        class ScriptedLLM:
            def __init__(self):
                self.calls = 0

            def generate(self, messages, system_prompt):
                self.calls += 1
                if self.calls == 1:
                    return 'Thought: 查询天气\nAction: get_weather(city="台州")'
                return 'Thought: 完成\nAction: Finish[台州晴。]'

        with patch("tools.weather_tool.get_weather", return_value="台州晴，20摄氏度") as weather:
            agent = ReActAgent("CLI 旅行助手", ScriptedLLM(), create_travel_tool_registry(), "工具：{tools}", AgentConfig(max_steps=2))
            with redirect_stdout(StringIO()):
                answer = agent.run("台州天气如何？")
        self.assertEqual(answer, "台州晴。")
        self.assertEqual(agent.tool_registry.get_execution_records()[0].name, "get_weather")
        weather.assert_called_once_with("台州")

    def test_web_agent_has_fresh_read_only_tools_and_history(self):
        llm = object()
        first = create_web_travel_agent(llm, AgentConfig(max_steps=2))
        second = create_web_travel_agent(llm, AgentConfig(max_steps=2))

        self.assertIsNot(first, second)
        self.assertIsNot(first.tool_registry, second.tool_registry)
        self.assertEqual(first.get_history(), [])
        self.assertEqual(second.get_history(), [])
        for agent in (first, second):
            self.assertTrue(agent.tool_registry.has_tool("get_weather"))
            self.assertTrue(agent.tool_registry.has_tool("search_travel_evidence"))
            self.assertFalse(agent.tool_registry.has_tool("memory"))
            self.assertFalse(agent.tool_registry.has_tool("save_itinerary"))
            self.assertFalse(agent.tool_registry.has_tool("delete_itinerary"))

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
