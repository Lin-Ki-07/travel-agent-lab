"""组装对话上下文并校验 Agent 输出；不修改行程。"""

import json

from pydantic import ValidationError

from agents.conversation_agent import ConversationAgent
from core.chat_contract import AnswerResponse, ChatRequest, ClarifyResponse, EditTargetResponse, chat_response_adapter
from core.exceptions import LLMError
from core.trip_models import Itinerary


def itinerary_summary(itinerary: Itinerary) -> str:
    places = {place.place_id: place.name for place in itinerary.places}
    lines = [f"目的地：{itinerary.request.destination}；出发日期：{itinerary.request.start_date.isoformat()}"]
    for day in itinerary.daily_plans:
        activities = "、".join(
            f"第 {index} 项（activity_index={index - 1}，place_id={activity.place_id}）"
            f"{places.get(activity.place_id, activity.place_id)} "
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
    if isinstance(response, EditTargetResponse):
        if itinerary is None:
            return ClarifyResponse(message="请先生成行程，再说明要调整的活动。")
        target = response.target
        if target.day_number > len(itinerary.daily_plans):
            return ClarifyResponse(message="我无法确定要调整哪项活动，请说明第几天第几项。")
        day = itinerary.daily_plans[target.day_number - 1]
        if target.activity_index >= len(day.activities) or day.activities[target.activity_index].place_id != target.place_id:
            return ClarifyResponse(message="我无法确定要调整哪项活动，请说明第几天第几项。")
        return response
    if not isinstance(response, (AnswerResponse, ClarifyResponse)):
        raise LLMError("当前对话步骤尚不接受编辑草案")
    return response
