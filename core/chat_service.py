"""组装对话上下文并校验 Agent 输出；不修改行程。"""

import json

from pydantic import ValidationError

from agents.conversation_agent import ConversationAgent
from core.chat_contract import AnswerResponse, ChatRequest, ClarifyResponse, chat_response_adapter
from core.exceptions import LLMError
from core.trip_models import Itinerary


def itinerary_summary(itinerary: Itinerary) -> str:
    places = {place.place_id: place.name for place in itinerary.places}
    lines = [f"目的地：{itinerary.request.destination}；出发日期：{itinerary.request.start_date.isoformat()}"]
    for day in itinerary.daily_plans:
        activities = "、".join(
            f"第 {index} 项 {places.get(activity.place_id, activity.place_id)} "
            f"{activity.start_time:%H:%M}-{activity.end_time:%H:%M}：{activity.description}"
            for index, activity in enumerate(day.activities, start=1)
        )
        lines.append(f"第 {day.day_number} 天（{day.plan_date.isoformat()}）：{activities}")
    return "\n".join(lines)


def reply_to_chat(agent: ConversationAgent, request: ChatRequest, itinerary: Itinerary | None):
    summary = itinerary_summary(itinerary) if itinerary else None
    raw = agent.run(request.text, request.history, summary)
    try:
        response = chat_response_adapter.validate_python(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMError("模型返回的对话响应不符合协议") from exc
    if not isinstance(response, (AnswerResponse, ClarifyResponse)):
        raise LLMError("当前对话步骤尚不接受编辑草案")
    return response
