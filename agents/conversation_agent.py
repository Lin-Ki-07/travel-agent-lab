from core.chat_contract import (
    AnswerResponse,
    ChatMessage,
    ClarifyResponse,
)
from core.llm_client import OpenAICompatibleClient
from core.message import Message


SYSTEM_PROMPT = """你是 Travel Agent Lab 的旅行对话助手。
请用中文直接回答旅行相关问题。当前行程摘要如果存在，只能作为回答依据；
不要声称已修改或保存行程，不要编造没有提供的地点、时间、天气或费用。
用户提出修改行程、但目标或要求不清楚时，提出一个具体追问。
当前步骤不能生成修改草案，也不能调用工具或执行保存。

只输出一个 JSON 对象，不要 Markdown 代码围栏：
普通回答：{"kind":"answer","message":"回答内容"}
需要追问：{"kind":"clarify","message":"具体问题"}
"""


class ConversationAgent:
    def __init__(self, llm: OpenAICompatibleClient):
        self.llm = llm

    def run(
        self,
        text: str,
        history: list[ChatMessage],
        itinerary_summary: str | None = None,
    ) -> str:
        messages = [
            Message(role=item.role, content=item.content)
            for item in history[-12:]
        ]
        if itinerary_summary:
            messages.append(
                Message(
                    role="system",
                    content=f"当前行程摘要（仅供回答参考）：\n{itinerary_summary}",
                )
            )
        messages.append(Message(role="user", content=text))
        return self.llm.generate(messages, system_prompt=SYSTEM_PROMPT)