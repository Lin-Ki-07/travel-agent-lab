from openai import OpenAI
from dotenv import load_dotenv

from core.message import Message

load_dotenv() 

class OpenAICompatibleClient:
    """
    一个用于调用任何兼容OpenAI接口的LLM服务的客户端。
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> str:
        """使用结构化消息调用 LLM。"""
        print("正在调用大语言模型...")

        try:
            api_messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ]

            for message in messages:
                if message.role == "tool":
                    api_messages.append(
                        {
                            "role": "user",
                            "content": f"Observation: {message.content}",
                        }
                    )
                else:
                    api_messages.append(message.to_dict())

            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                stream=False,
            )

            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer

        except Exception as exc:
            print(f"调用LLM API时发生错误: {exc}")
            return "错误:调用语言模型服务时出错。"
