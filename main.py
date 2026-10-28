from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from core.config import AgentConfig, LLMConfig
from core.exceptions import LLMError

from tools.weather_tool import WeatherTool
from tools.registry import ToolRegistry, ToolParameter
from tools.attraction_tool import get_attraction
from tools.memory_tool import MemoryTool

from agents.react_agent import ReActAgent

from memory.sqlite_store import SQLiteMemoryStore


# 读取系统提示词
with open("prompts/system_prompt.md", "r", encoding="utf-8") as f:
    AGENT_SYSTEM_PROMPT = f.read()

# 注册工具
tool_registry = ToolRegistry()

tool_registry.register_tool(WeatherTool())

tool_registry.register_function(
    name="get_attraction",
    func=get_attraction,
    description="根据城市和天气推荐旅游景点",
    parameters=[
        ToolParameter(
            name="city",
            type="string",
            description="旅游城市名称",
        ),
        ToolParameter(
            name="weather",
            type="string",
            description="该城市当前天气描述",
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

    print("旅行助手已启动。输入 /new 开始新对话，输入 /quit 退出。")

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
        
        try:
            answer = agent.run(question)
        except LLMError as exc:
            print(f"任务失败: {exc}")
        else:
            print(f"助手：{answer}")
