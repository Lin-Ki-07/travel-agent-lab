from openai import OpenAI, APIError
from dotenv import load_dotenv

from core.message import Message
from core.exceptions import LLMError

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

            if not response.choices:
                raise LLMError("模型响应没有包含候选答案")

            answer = response.choices[0].message.content

            if not answer or not answer.strip():
                raise LLMError("模型返回了空内容")

            print("大语言模型响应成功。")
            return answer

        except APIError as exc:
            raise LLMError(
                    f"模型请求失败: {exc}"
                ) from exc
