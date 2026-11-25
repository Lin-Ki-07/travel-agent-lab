"""核对替换目标并组装只读草案。"""

from agents.edit_draft_agent import EditDraftAgent
from collections.abc import Callable
from core.chat_contract import DraftActivity, DraftTransport, EditDraft, EditDraftResponse
from core.trip_edit import edit_day
from core.trip_models import Itinerary
from core.trip_store import itinerary_fingerprint, update_itinerary_if_unchanged
from dataclasses import asdict
from fastapi.encoders import jsonable_encoder
from core.map_view import build_map_days


def generate_edit_draft(
    agent_factory: Callable[[], EditDraftAgent],
    itinerary: Itinerary,
    plan_id: str,
    day_number: int,
    activity_index: int,
    original_place_id: str,
    candidate_place_id: str,
) -> EditDraftResponse:
    if not 1 <= day_number <= len(itinerary.daily_plans):
        raise ValueError("目标行程日不存在")
    day = itinerary.daily_plans[day_number - 1]
    if not 0 <= activity_index < len(day.activities):
        raise ValueError("目标活动不存在")
    original = day.activities[activity_index]
    if original.place_id != original_place_id:
        raise ValueError("目标活动已变化")
    places = {place.place_id: place for place in itinerary.places}
    if candidate_place_id == original_place_id or candidate_place_id not in places:
        raise ValueError("候选地点无效")
    if candidate_place_id in {activity.place_id for activity in day.activities}:
        raise ValueError("候选地点已在当天行程中")

    before = day.activities[activity_index - 1] if activity_index > 0 else None
    after = day.activities[activity_index + 1] if activity_index + 1 < len(day.activities) else None
    context = (
        f"目的地：{itinerary.request.destination}；第 {day_number} 天：{day.plan_date.isoformat()}\n"
        f"原地点：{places[original_place_id].name}；原活动：{original.description}；"
        f"时间：{original.start_time:%H:%M}-{original.end_time:%H:%M}\n"
        f"候选地点：{places[candidate_place_id].name}；地址：{places[candidate_place_id].address}\n"
        f"前一地点：{places[before.place_id].name if before else '无'}；"
        f"后一地点：{places[after.place_id].name if after else '无'}"
    )
    suggestion = agent_factory().suggest(context)

    activities = [
        DraftActivity(
            place_id=candidate_place_id if index == activity_index else activity.place_id,
            description=suggestion.description if index == activity_index else activity.description,
            start_time=activity.start_time.strftime("%H:%M"),
            end_time=activity.end_time.strftime("%H:%M"),
        )
        for index, activity in enumerate(day.activities)
    ]
    routes = {(segment.from_place_id, segment.to_place_id): segment for segment in day.transport_segments}
    transports = []
    for index in range(len(activities) - 1):
        start, end = activities[index].place_id, activities[index + 1].place_id
        if start == end:
            continue
        old_start = day.activities[index].place_id
        old_end = day.activities[index + 1].place_id
        prior = routes.get((old_start, old_end))
        if prior is None:
            raise ValueError("原行程交通连接不完整")
        mode, minutes = prior.mode, None if index in (activity_index - 1, activity_index) else prior.estimated_minutes
        transports.append(DraftTransport(
            from_place_id=start, to_place_id=end, mode=mode, estimated_minutes=minutes,
        ))

    edit_day(itinerary, day_number, {
        "activities": [item.model_dump() for item in activities],
        "transport_segments": [item.model_dump() for item in transports],
    })
    return EditDraftResponse(
        message="替换草案已生成，原行程尚未修改。",
        draft=EditDraft(
            plan_id=plan_id, source_fingerprint=itinerary_fingerprint(itinerary), day_number=day_number, activity_index=activity_index,
            original_place_id=original_place_id, candidate_place_id=candidate_place_id,
            activities=activities, transport_segments=transports,
        ),
    )


def confirm_edit_draft(itinerary: Itinerary, plan_id: str, draft: EditDraft) -> dict:
    if draft.plan_id != plan_id or draft.source_fingerprint != itinerary_fingerprint(itinerary):
        raise ValueError("草案已过期，请重新生成")
    if not 1 <= draft.day_number <= len(itinerary.daily_plans):
        raise ValueError("目标行程日不存在")
    day = itinerary.daily_plans[draft.day_number - 1]
    if not 0 <= draft.activity_index < len(day.activities):
        raise ValueError("目标活动不存在")
    if day.activities[draft.activity_index].place_id != draft.original_place_id:
        raise ValueError("目标活动已变化")
    place_ids = {place.place_id for place in itinerary.places}
    if draft.candidate_place_id not in place_ids or draft.candidate_place_id in {item.place_id for item in day.activities}:
        raise ValueError("候选地点无效")
    if len(draft.activities) != len(day.activities):
        raise ValueError("草案活动数量不匹配")
    for index, (old, new) in enumerate(zip(day.activities, draft.activities)):
        expected_id = draft.candidate_place_id if index == draft.activity_index else old.place_id
        if new.place_id != expected_id:
            raise ValueError("草案修改了非目标地点")
        if new.start_time != old.start_time.strftime("%H:%M") or new.end_time != old.end_time.strftime("%H:%M"):
            raise ValueError("草案修改了活动时间")
        if index != draft.activity_index and new.description != old.description:
            raise ValueError("草案修改了其他活动")

    edited = edit_day(itinerary, draft.day_number, {
        "activities": [item.model_dump() for item in draft.activities],
        "transport_segments": [item.model_dump() for item in draft.transport_segments],
    })
    if not update_itinerary_if_unchanged(plan_id, edited, draft.source_fingerprint):
        raise ValueError("行程已变化，请重新生成草案")
    return {
        "plan_id": plan_id,
        "itinerary": jsonable_encoder(asdict(edited)),
        "map_days": build_map_days(edited),
    }
