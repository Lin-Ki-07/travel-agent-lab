from core.trip_models import Place, TripRequest, WeatherSnapshot
from tools.amap_place_tool import search_amap_places
from tools.attraction_tool import search_travel_evidence
from tools.trip_weather_tool import get_trip_weather


def gather_trip_sources(
    request: TripRequest,
) -> tuple[list[Place], list[WeatherSnapshot], str]:
    """获取规划所需资料；关键来源失败时给出明确错误。"""
    try:
        places = search_amap_places(request.destination)
    except (ValueError, RuntimeError) as exc:
        raise RuntimeError(f"地点查询失败：{exc}") from exc

    if not places:
        raise RuntimeError("地点查询成功，但没有可用的真实地点")

    try:
        weather = get_trip_weather(
            request.destination,
            request.start_date,
            request.days,
        )
    except (ValueError, RuntimeError) as exc:
        raise RuntimeError(f"天气查询失败：{exc}") from exc

    preferences = "、".join(request.preferences) or "一般旅行"
    question = (
        f"{request.destination}适合{preferences}的旅行地点、"
        "游览安排与注意事项"
    )
    evidence = search_travel_evidence(question)

    if evidence.startswith(("错误:", "搜索失败：")):
        raise RuntimeError(f"网页资料搜索失败：{evidence}")

    return places, weather, evidence