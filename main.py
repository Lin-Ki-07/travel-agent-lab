from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from tools.weather_tool import get_weather
from tools.attraction_tool import get_attraction
from agents.react_agent import ReActAgent

# 读取系统提示词
with open("prompts/system_prompt.md", "r", encoding="utf-8") as f:
    AGENT_SYSTEM_PROMPT = f.read()

# 注册工具
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}

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
    question = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    answer = ReActAgent(question)
    print(f"运行结果: {answer}")