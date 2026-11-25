"""为已确定的地点替换生成有限的自然语言建议。"""

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.exceptions import LLMError
from core.llm_client import OpenAICompatibleClient
from core.message import Message


class DraftSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    description: str = Field(min_length=1)
    incoming_mode: str | None = None
    outgoing_mode: str | None = None


SYSTEM_PROMPT = """你是智能旅行助手，帮助用户调整已有旅行规划。
程序已经确定待替换活动和候选地点。你只建议新活动描述及相邻交通方式。
保留原活动时间；不要修改地点 ID、其他活动或行程，不要声称已经保存。
只输出 JSON 对象，不要 Markdown：
{"description":"新活动描述","incoming_mode":"到达该地点的交通方式或 null","outgoing_mode":"离开该地点的交通方式或 null"}
没有前一项活动时 incoming_mode 必须为 null；没有后一项活动时 outgoing_mode 必须为 null。
"""


class EditDraftAgent:
    def __init__(self, llm: OpenAICompatibleClient):
        self.llm = llm

    def suggest(self, context: str) -> DraftSuggestion:
        raw = self.llm.generate(
            [Message(role="user", content=context)],
            system_prompt=SYSTEM_PROMPT,
        )
        try:
            return DraftSuggestion.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMError("模型返回的编辑建议不符合协议") from exc
