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


def enrich_trip_routes(itinerary: Itinerary) -> Itinerary:
    """为新行程所有交通段补充快照；未知方式及查询失败不阻断行程。"""
    validate_itinerary(itinerary)
    places = {place.place_id: place for place in itinerary.places}
    days = []
    for day in itinerary.daily_plans:
        segments = []
        for segment in day.transport_segments:
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
            minutes = ((route.duration_seconds + 59) // 60 if route.status == "ok" else None)
            segments.append(replace(segment, route=route, estimated_minutes=minutes))
        days.append(replace(day, transport_segments=segments))
    return validate_itinerary(replace(itinerary, daily_plans=days))
