"""显式补齐交通端点城市编码，不查询路线或写数据库。"""

from dataclasses import replace

from core.itinerary_validator import validate_itinerary
from core.trip_models import Itinerary
from tools.amap_place_tool import query_amap_citycode


def complete_endpoint_citycodes(itinerary: Itinerary) -> tuple[Itinerary, int, int]:
    """返回新行程、补齐ID数、仍缺失端点ID数；故障交由调用者中止保存。"""
    validate_itinerary(itinerary)
    endpoint_ids = {pid for day in itinerary.daily_plans for segment in day.transport_segments
                    for pid in (segment.from_place_id, segment.to_place_id)}
    codes = {}
    for place in itinerary.places:
        if (place.place_id in endpoint_ids and place.source == "amap"
                and place.citycode is None and place.place_id not in codes):
            codes[place.place_id] = query_amap_citycode(place.place_id)
    places = [replace(place, citycode=codes[place.place_id])
              if place.source == "amap" and place.citycode is None
              and codes.get(place.place_id) is not None else place
              for place in itinerary.places]
    updated = validate_itinerary(replace(itinerary, places=places))
    completed = sum(code is not None for code in codes.values())
    missing = {p.place_id for p in places if p.place_id in endpoint_ids and p.citycode is None}
    return updated, completed, len(missing)
