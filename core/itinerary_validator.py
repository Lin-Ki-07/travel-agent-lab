import json
import logging
import re
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

logger = logging.getLogger(__name__)

_FENCE_PATTERN = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def extract_json_text(raw: str) -> str:
    """去掉模型常见的 Markdown 代码围栏，并截取最外层的 JSON 对象文本。

    只做格式层面的清理，不修改 JSON 内容；内容是否合法仍由 json.loads 判断。
    """
    text = raw.strip()
    fenced = _FENCE_PATTERN.match(text)
    if fenced:
        text = fenced.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start:end + 1]
    return text


def parse_itinerary(
    raw: str,
    request: TripRequest,
    places: list[Place],
    weather: list[WeatherSnapshot],
) -> Itinerary:
    """解析并校验模型返回的结构化 JSON。"""
    try:
        data = json.loads(extract_json_text(raw))
    except json.JSONDecodeError as exc:
        # 记录原始输出的前若干字符，便于定位模型实际返回的格式；不记录密钥。
        logger.warning("行程 JSON 解析失败，模型原始输出（截断）：%r", raw[:2000])
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

        for previous, current in zip(activities, activities[1:]):
            if current.start_time < previous.start_time:
                raise ValueError(f"第 {index} 天活动未按开始时间排序")
            if current.start_time < previous.end_time:
                raise ValueError(f"第 {index} 天活动时间重叠")

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

        expected_routes = [
            (previous.place_id, current.place_id)
            for previous, current in zip(activities, activities[1:])
            if previous.place_id != current.place_id
        ]
        actual_routes = [
            (segment.from_place_id, segment.to_place_id)
            for segment in transport_segments
        ]
        if actual_routes != expected_routes:
            raise ValueError(f"第 {index} 天交通段必须按活动地点顺序连接")

        try:
            daily_plans.append(
                DailyPlan(
                    day_number=index,
                    plan_date=plan_date,
                    weather=weather_map[plan_date],
                    activities=activities,
                    transport_segments=transport_segments,
                    estimated_cost_cny=item["estimated_cost_cny"],
                    cost_basis=item["cost_basis"],
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 天预算字段不合法：{exc}") from exc

    try:
        estimated_total_cny = data["estimated_total_cny"]
    except KeyError as exc:
        raise ValueError("缺少 estimated_total_cny 字段") from exc

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