from core.trip_models import Itinerary


def build_map_days(itinerary: Itinerary) -> list[dict]:
    """从已校验行程派生地图快照，不查询外部服务。"""
    place_by_id = {place.place_id: place for place in itinerary.places}
    map_days = []

    for day in itinerary.daily_plans:
        stops = []
        for order, activity in enumerate(day.activities, start=1):
            place = place_by_id[activity.place_id]
            stops.append({
                "order": order,
                "place_id": place.place_id,
                "name": place.name,
                "position": [place.longitude, place.latitude],
            })

        line_positions = []
        previous_place_id = None
        for stop in stops:
            if stop["place_id"] != previous_place_id:
                line_positions.append(stop["position"])
            previous_place_id = stop["place_id"]

        segments = []
        # 按活动连接顺序消费交通段，重复地点不产生额外连接。
        transport = iter(day.transport_segments)
        for origin, destination in zip(stops, stops[1:]):
            if origin["place_id"] == destination["place_id"]:
                continue
            segment = next(transport)
            route = segment.route
            segments.append({
                "from_order": origin["order"],
                "to_order": destination["order"],
                "kind": "route_snapshot" if route and route.status == "ok" else "place_order_schematic",
                "parts": [{"mode": part.mode, "positions": [list(p) for p in part.positions]}
                          for part in route.parts] if route and route.status == "ok" else [],
                "fallback_positions": [origin["position"], destination["position"]],
            })

        map_days.append({
            "day_number": day.day_number,
            "plan_date": day.plan_date.isoformat(),
            "stops": stops,
            "segments": segments,
            "line": {
                "kind": "place_order_schematic",
                "label": "地点顺序示意线，非实际道路路线",
                "positions": line_positions,
            },
        })

    return map_days
