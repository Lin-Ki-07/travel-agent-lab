from core.llm_client import OpenAICompatibleClient
from core.trip_models import Itinerary
from core.trip_planner import generate_itinerary
from core.trip_sources import gather_trip_sources
from core.trip_input import parse_trip_request


def plan_trip(
    llm: OpenAICompatibleClient,
    raw_request: dict[str, str],
) -> Itinerary:
    """把外部输入转换为请求，并复用 v0.3.0 的完整规划与校验流程。"""
    request = parse_trip_request(raw_request)
    places, weather, evidence = gather_trip_sources(request)
    return generate_itinerary(
        llm,
        request,
        places,
        weather,
        evidence,
    )