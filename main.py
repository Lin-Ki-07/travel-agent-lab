from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os
import sqlite3

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from core.config import AgentConfig, LLMConfig
from core.exceptions import LLMError
from core.trip_planner import generate_itinerary
from core.trip_sources import gather_trip_sources

from tools.weather_tool import WeatherTool
from tools.registry import ToolRegistry, ToolParameter
from tools.attraction_tool import search_travel_evidence
from tools.memory_tool import MemoryTool

from agents.react_agent import ReActAgent

from memory.sqlite_store import SQLiteMemoryStore

from commands.memory_commands import handle_memory_command
from commands.trip_commands import collect_trip_request
from commands.trip_output import format_itinerary

# 读取系统提示词
with open("prompts/system_prompt.md", "r", encoding="utf-8") as f:
    AGENT_SYSTEM_PROMPT = f.read()

# 注册工具
tool_registry = ToolRegistry()

tool_registry.register_tool(WeatherTool())

tool_registry.register_function(
    name="search_travel_evidence",
    func=search_travel_evidence,
    description="按旅行问题搜索网页资料，返回编号、标题、URL 和文本证据",
    parameters=[
        ToolParameter(
            name="question",
            type="string",
            description="需要检索的完整旅行问题",
        ),
    ],
)

# 启动入口
if __name__ == "__main__":
    memory_store = SQLiteMemoryStore("data/memory.db")
    tool_registry.register_tool(MemoryTool(memory_store))

    agent_config = AgentConfig.from_env()

    llm_config = LLMConfig.from_env()
    
    llm = OpenAICompatibleClient(
            model=llm_config.model,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            timeout=llm_config.timeout,
            temperature=llm_config.temperature,
        )

    agent = ReActAgent(
        name = "旅行助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt=AGENT_SYSTEM_PROMPT,
        config=agent_config,
    )

    print(
        "你的专属旅行助手已就位！\n"
        "你可以输入：\n"
        "/memory-help：查看长期记忆命令；\n"
        "/new：开始新对话；\n"
        "/history：查看对话历史；\n"
        "/plan：填写需求并生成逐日行程；\n"
        "/quit：退出。\n"
        "也可以直接和我对话。"
    )

    while True:
        try:
            question = input("\n你：").strip()
        except LLMError as exc:
            print(f"任务失败: {exc}")
      
        if not question:
            continue

        if question == "/quit":
            print("已退出。")
            break

        if question == "/new":
            agent.clear_history()
            print("已清空当前对话历史。")
            continue

        if question == "/history":
            print("\n当前对话历史：")
            for message in agent.get_history():
                print(message)
            continue

        if question == "/plan":
            try:
                request = collect_trip_request()
                places, weather, evidence = gather_trip_sources(request)
                trip = generate_itinerary(
                    llm, request, places, weather, evidence
                )
                print(format_itinerary(trip))
            except (ValueError, RuntimeError) as exc:
                print(f"行程规划失败：{exc}")
            continue

        try:
            command_result = handle_memory_command(question, memory_store)
        except (sqlite3.Error, ValueError) as exc:
            print(f"记忆操作失败：{exc}")
            continue

        if command_result is not None:
            print(f"助手：{command_result}")
            continue

        try:
            answer = agent.run(question)
        except LLMError as exc:
            print(f"任务失败: {exc}")
        else:
            print(f"助手：{answer}")
