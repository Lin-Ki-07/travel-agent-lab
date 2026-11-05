import json
from datetime import date, datetime, time

from core.trip_models import (
    Activity,
    DailyPlan,
    Itinerary,
    Place,
    TripRequest,
    TransportSegment,
    WeatherSnapshot,
)


def parse_itinerary(
    raw: str,
    request: TripRequest,
    places: list[Place],
    weather: list[WeatherSnapshot],
) -> Itinerary:
    """解析并校验模型返回的结构化 JSON。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("模型输出不是合法 JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("模型输出必须是 JSON 对象")

    daily_data = data.get("daily_plans")
    if not isinstance(daily_data, list):
        raise ValueError("缺少 daily_plans 列表")

    place_map = {place.place_id: place for place in places}
    weather_map = {item.forecast_date: item for item in weather}
    daily_plans: list[DailyPlan] = []

    for index, item in enumerate(daily_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 天不是对象")

        try:
            plan_date = date.fromisoformat(item["plan_date"])
            activities_data = item["activities"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 天缺少必要字段") from exc

        if plan_date not in weather_map:
            raise ValueError(f"第 {index} 天没有对应天气数据")
        if not isinstance(activities_data, list) or not activities_data:
            raise ValueError(f"第 {index} 天必须至少包含一项活动")

        activities: list[Activity] = []
        for activity_data in activities_data:
            try:
                place_id = activity_data["place_id"]
                activity = Activity(
                    place_id=place_id,
                    description=activity_data["description"],
                    start_time=time.fromisoformat(activity_data["start_time"]),
                    end_time=time.fromisoformat(activity_data["end_time"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"第 {index} 天存在非法活动") from exc

            if place_id not in place_map:
                raise ValueError(f"活动引用了未查询到的地点：{place_id}")
            activities.append(activity)

        transport_segments: list[TransportSegment] = []
        for transport_data in item.get("transport_segments", []):
            try:
                segment = TransportSegment(
                    from_place_id=transport_data["from_place_id"],
                    to_place_id=transport_data["to_place_id"],
                    mode=transport_data["mode"],
                    estimated_minutes=transport_data.get("estimated_minutes"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"第 {index} 天存在非法交通段") from exc

            if (
                segment.from_place_id not in place_map
                or segment.to_place_id not in place_map
            ):
                raise ValueError(f"交通段引用了未查询到的地点")
            transport_segments.append(segment)

        daily_plans.append(
            DailyPlan(
                day_number=index,
                plan_date=plan_date,
                weather=weather_map[plan_date],
                activities=activities,
                transport_segments=transport_segments,
            )
        )

    estimated_total_cny = data.get("estimated_total_cny")
    if estimated_total_cny is not None and not isinstance(
        estimated_total_cny, int
    ):
        raise ValueError("estimated_total_cny 必须是整数或 null")

    return Itinerary(
        request=request,
        places=places,
        daily_plans=daily_plans,
        estimated_total_cny=estimated_total_cny,
        generated_at=datetime.now().astimezone(),
    )