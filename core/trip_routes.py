"""由确定性后端流程补充路线事实，不调用模型。"""

from dataclasses import replace
from datetime import datetime, timezone

from core.itinerary_validator import validate_itinerary
from core.trip_models import Itinerary, RouteSnapshot
from tools.amap_route_tool import query_amap_route


# 仅匹配明确方式，不根据描述猜测出行方式。
MODE_ALIASES = {
    "步行": "walking", "walking": "walking",
    "驾车": "driving", "自驾": "driving", "driving": "driving",
    "公交": "transit", "公共交通": "transit", "地铁": "transit", "transit": "transit",
}


def _query_segment_route(segment, places) -> RouteSnapshot:
    mode = MODE_ALIASES.get(segment.mode.strip().lower())
    reason = None
    if mode is None:
        reason = "不支持的交通方式，未查询路线"
    elif mode == "transit":
        reason = "公交查询缺少可靠城市编码，未查询路线"
    if reason:
        route = RouteSnapshot("failed", "amap", datetime.now(timezone.utc),
                              failure_reason=reason)
    else:
        route = query_amap_route(places[segment.from_place_id],
                                 places[segment.to_place_id], mode)
    return route


def enrich_trip_routes(itinerary: Itinerary) -> Itinerary:
    """为新行程所有交通段补充快照；未知方式及查询失败不阻断行程。"""
    validate_itinerary(itinerary)
    places = {place.place_id: place for place in itinerary.places}
    days = []
    for day in itinerary.daily_plans:
        segments = []
        for segment in day.transport_segments:
            route = _query_segment_route(segment, places)
            minutes = ((route.duration_seconds + 59) // 60 if route.status == "ok" else None)
            segments.append(replace(segment, route=route, estimated_minutes=minutes))
        days.append(replace(day, transport_segments=segments))
    return validate_itinerary(replace(itinerary, daily_plans=days))


def refresh_edited_day_routes(
    original: Itinerary, edited: Itinerary, day_number: int,
) -> Itinerary:
    """只更新编辑日；快照只从旧行程复用，不信任编辑结果携带的路线事实。

    调用者负责先校验编辑，再在保存入口调用本函数；草案生成不得调用。
    复用的是既有查询快照，不表示重新查询或保证当前交通状况。
    """
    validate_itinerary(original)
    validate_itinerary(edited)
    if not 1 <= day_number <= min(len(original.daily_plans), len(edited.daily_plans)):
        raise ValueError("行程日序号不存在")
    old_day = original.daily_plans[day_number - 1]
    new_day = edited.daily_plans[day_number - 1]
    if original.request != edited.request or original.places != edited.places:
        raise ValueError("单日路线更新不能修改旅行需求或地点资料")
    if old_day.plan_date != new_day.plan_date:
        raise ValueError("单日路线更新不能修改行程日期")

    def identity(segment):
        text = segment.mode.strip().lower()
        # 未知方式不能全部归为 None，否则不同未知方式会错误匹配。
        mode = MODE_ALIASES.get(text, text)
        return segment.from_place_id, segment.to_place_id, mode

    prior = {identity(segment): segment for segment in old_day.transport_segments}
    segments = []
    pending = []
    for index, segment in enumerate(new_day.transport_segments):
        previous = prior.get(identity(segment))
        if previous is not None and previous.route is not None:
            segments.append(replace(segment, route=previous.route,
                                    estimated_minutes=previous.estimated_minutes))
        else:
            segments.append(replace(segment, route=None, estimated_minutes=None))
            pending.append(index)

    # 复用新行程查询规则，仅查询待更新段。
    if pending:
        places = {place.place_id: place for place in edited.places}
        for index in pending:
            segment = segments[index]
            route = _query_segment_route(segment, places)
            minutes = ((route.duration_seconds + 59) // 60 if route.status == "ok" else None)
            segments[index] = replace(segment, route=route, estimated_minutes=minutes)
    days = list(edited.daily_plans)
    days[day_number - 1] = replace(new_day, transport_segments=segments)
    return validate_itinerary(replace(edited, daily_plans=days))
