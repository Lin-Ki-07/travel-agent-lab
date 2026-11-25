from core.chat_contract import ChatMessage
from core.llm_client import OpenAICompatibleClient
from core.message import Message


SYSTEM_PROMPT = """你是 Travel Agent Lab 的旅行对话助手。
请用中文直接回答旅行相关问题。当前行程摘要如果存在，只能作为回答依据；
不要声称已修改或保存行程，不要编造没有提供的地点、时间、天气或费用。
用户提出修改行程、但目标或要求不清楚时，提出一个具体追问。
当前步骤不能生成修改草案，也不能调用工具或执行保存。

只输出一个 JSON 对象，不要 Markdown 代码围栏：
普通旅行问题：{"kind":"answer","message":"回答内容"}
无法唯一定位要修改的活动：{"kind":"clarify","message":"请说明第几天第几项，或地点名称"}
已唯一定位要修改的活动：
{"kind":"edit_target","message":"已定位目标，尚未修改行程","target":{"day_number":1,"activity_index":0,"place_id":"地点 ID"}}

只有用户明确要求调整行程时才输出 edit_target。普通提问即使提到地点，也输出 answer。
day_number 从 1 开始，activity_index 从 0 开始；数字和地点 ID 必须来自当前行程摘要。
若用户只说“换一下”、同名地点出现多次，或无法确定目标，输出 clarify。
edit_target 仅是定位建议，不表示已生成草案、修改或保存行程。
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