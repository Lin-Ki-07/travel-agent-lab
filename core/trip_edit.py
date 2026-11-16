from dataclasses import replace
from datetime import time

from core.itinerary_validator import validate_itinerary
from core.trip_models import Activity, Itinerary, TransportSegment


def edit_day(
    itinerary: Itinerary,
    day_number: int,
    raw: dict,
) -> Itinerary:
    """用完整的活动和交通段替换一天；不修改传入的原行程。"""
    if not 1 <= day_number <= len(itinerary.daily_plans):
        raise ValueError("行程日序号不存在")
    if not isinstance(raw, dict):
        raise ValueError("编辑内容必须是对象")

    activity_data = raw.get("activities")
    transport_data = raw.get("transport_segments")
    if not isinstance(activity_data, list) or not activity_data:
        raise ValueError("每天必须至少包含一项活动")
    if not isinstance(transport_data, list):
        raise ValueError("transport_segments 必须是列表")

    activities = []
    for item in activity_data:
        if not isinstance(item, dict):
            raise ValueError("活动必须是对象")
        try:
            activities.append(Activity(
                place_id=item["place_id"],
                description=item["description"],
                start_time=time.fromisoformat(item["start_time"]),
                end_time=time.fromisoformat(item["end_time"]),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"活动字段不合法：{exc}") from exc

    segments = []
    for item in transport_data:
        if not isinstance(item, dict):
            raise ValueError("交通段必须是对象")
        try:
            segments.append(TransportSegment(
                from_place_id=item["from_place_id"],
                to_place_id=item["to_place_id"],
                mode=item["mode"],
                estimated_minutes=item.get("estimated_minutes"),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"交通段字段不合法：{exc}") from exc

    original_day = itinerary.daily_plans[day_number - 1]
    edited_day = replace(
        original_day,
        activities=activities,
        transport_segments=segments,
        estimated_cost_cny=None,
        cost_basis=None,
    )
    days = list(itinerary.daily_plans)
    days[day_number - 1] = edited_day

    return validate_itinerary(replace(
        itinerary,
        daily_plans=days,
        estimated_total_cny=None,
    ))