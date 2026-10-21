from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from tools.weather_tool import get_weather
from tools.attraction_tool import get_attraction
from agents.react_agent import ReActAgent
from tools.registry import ToolRegistry, ToolParameter
from core.config import AgentConfig
from core.exceptions import LLMError

# 读取系统提示词
with open("prompts/system_prompt.md", "r", encoding="utf-8") as f:
    AGENT_SYSTEM_PROMPT = f.read()

# 注册工具
tool_registry = ToolRegistry()

tool_registry.register_function(
    name="get_weather",
    func=get_weather,
    description="查询指定城市的当前天气",
    parameters=[
        ToolParameter(
            name="city",
            type="string",
            description="要查询天气的城市名称",
        ),
    ],
)

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
    config = AgentConfig.from_env()
    
    llm = OpenAICompatibleClient(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            temperature=config.temperature,
        )

    agent = ReActAgent(
        name = "旅行助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt=AGENT_SYSTEM_PROMPT,
        config=config,
    )

    question = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"

    try:
        answer = agent.run(question)
    except LLMError as exc:
        print(f"任务失败: {exc}")
    else:
        print(f"运行结果: {answer}")

    print("\n本次任务历史：")
    print("\n工具执行记录：")
    for record in tool_registry.get_execution_records():
        print(
            f"{record.name} "
            f"参数={record.arguments} "
            f"耗时={record.duration_ms:.2f}ms "
            f"成功={record.success}"
        )
    for message in agent.get_history():
        print(message)