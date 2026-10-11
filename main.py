from dotenv import load_dotenv
load_dotenv()  # 加载 .env

import os
import re

# 导入自定义模块
from core.llm_client import OpenAICompatibleClient
from tools.weather_tool import get_weather
from tools.attraction_tool import get_attraction

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

def run_agent(user_prompt: str,max_steps:int = 5) -> str:
    prompt_history = [f"用户请求: {user_prompt}"]

    print(f"用户输入: {user_prompt}\n" + "="*40)

    # --- 运行主循环 ---
    for i in range(max_steps): 
        print(f"--- 循环 {i+1} ---\n")
        
        #  构建Prompt
        full_prompt = "\n".join(prompt_history)
        
        #  调用LLM进行思考
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
        # 模型可能会输出多余的Thought-Action，需要截断
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)
        
        # 解析并执行行动
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
            return final_answer
        
        tool_name = re.search(r"(\w+)\(", action_str).group(1)
        args_str = re.search(r"\((.*)\)", action_str).group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        # 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)

    # 达到循环上限
    return f"未能在 {max_steps} 步内完成任务。"

# 启动入口
if __name__ == "__main__":
    question = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    answer = run_agent(question, max_steps=5)
    print(f"运行结果: {answer}")