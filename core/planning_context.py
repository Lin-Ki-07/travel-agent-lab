import json
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from core.trip_models import Place, TripRequest, WeatherSnapshot


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"不支持序列化的类型: {type(value).__name__}")


def build_planning_context(
    request: TripRequest,
    places: list[Place],
    weather: list[WeatherSnapshot],
    web_evidence: str,
) -> str:
    """构造发送给模型的只读事实上下文。"""
    payload = {
        "request": asdict(request),
        "places": [asdict(place) for place in places],
        "weather": [asdict(snapshot) for snapshot in weather],
        "web_evidence": web_evidence.strip(),
        "rules": [
            "只能使用 places 中出现的 place_id、名称和坐标。",
            "天气 available=false 时，必须说明该日期暂无可用预报。",
            "交通耗时只能填写有依据的估算，并明确标记为估算；没有依据时留空。",
            "不得编造票价、班次、天气、地点 ID、坐标或精确路程耗时。",
            "最终必须输出 JSON，不要输出 Markdown 代码围栏或解释文字。",
        ],
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=_json_default,
    )