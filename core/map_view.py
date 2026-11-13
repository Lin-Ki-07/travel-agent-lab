from core.trip_models import Itinerary


def build_map_days(itinerary: Itinerary) -> list[dict]:
    """从已校验的行程生成按天排列的地点和示意线数据。"""
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

        map_days.append({
            "day_number": day.day_number,
            "plan_date": day.plan_date.isoformat(),
            "stops": stops,
            "line": {
                "kind": "place_order_schematic",
                "label": "地点顺序示意线，非实际道路路线",
                "positions": line_positions,
            },
        })

    return map_days