from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from tools.weather_tool import get_weather
from tools.attraction_tool import get_attraction
from agents.react_agent import ReActAgent
from tools.registry import ToolRegistry

# 读取系统提示词
with open("prompts/system_prompt.md", "r", encoding="utf-8") as f:
    AGENT_SYSTEM_PROMPT = f.read()

# 注册工具
tool_registry = ToolRegistry()

tool_registry.register_function(
    name="get_weather",
    func=get_weather,
    description="查询指定城市的当前天气",
)

tool_registry.register_function(
    name="get_attraction",
    func=get_attraction,
    description="根据城市和天气推荐旅游景点",
)

# 配置LLM客户端
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.environ.get("OPENAI_BASE_URL")
MODEL_ID = os.environ.get("MODEL_ID")

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# 启动入口
if __name__ == "__main__":
    agent = ReActAgent(
        llm=llm,
        tool_registry=tool_registry,
        system_prompt=AGENT_SYSTEM_PROMPT,
        max_steps=1,
    )

    question = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    answer = agent.run(question)
    print(f"运行结果: {answer}")