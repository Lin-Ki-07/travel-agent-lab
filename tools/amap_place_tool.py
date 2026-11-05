import os
from datetime import datetime, timezone

import requests

from core.trip_models import Place


AMAP_PLACE_SEARCH_URL = "https://restapi.amap.com/v3/place/text"


def search_amap_places(
    city: str,
    keyword: str = "景点",
    *,
    api_key: str | None = None,
) -> list[Place]:
    """查询高德地点，返回带来源和查询时间的候选地点。"""
    city = city.strip()
    keyword = keyword.strip()

    if not city:
        raise ValueError("地点搜索城市不能为空")
    if not keyword:
        raise ValueError("地点搜索关键词不能为空")

    key = api_key or os.getenv("AMAP_API_KEY")
    if not key:
        raise ValueError("未配置 AMAP_API_KEY")

    try:
        response = requests.get(
            AMAP_PLACE_SEARCH_URL,
            params={
                "key": key,
                "keywords": keyword,
                "city": city,
                "citylimit": "true",
                "offset": 20,
                "page": 1,
                "extensions": "base",
            },
            timeout=(5, 10),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("高德地点请求或响应解析失败") from exc

    if data.get("status") != "1":
        info = data.get("info") or "未知错误"
        raise RuntimeError(f"高德地点搜索失败：{info}")

    pois = data.get("pois")
    if not isinstance(pois, list):
        raise RuntimeError("高德地点响应缺少 pois 列表")

    queried_at = datetime.now(timezone.utc)
    places: list[Place] = []

    for poi in pois:
        if not isinstance(poi, dict):
            continue

        place_id = str(poi.get("id") or "").strip()
        name = str(poi.get("name") or "").strip()
        location = str(poi.get("location") or "").strip()
        if not place_id or not name or not location:
            continue

        try:
            longitude_text, latitude_text = location.split(",")
            longitude = float(longitude_text)
            latitude = float(latitude_text)
        except ValueError:
            continue

        address_value = poi.get("address")
        address = address_value.strip() if isinstance(address_value, str) else ""

        try:
            place = Place(
                place_id=place_id,
                name=name,
                address=address,
                latitude=latitude,
                longitude=longitude,
                source="amap",
                queried_at=queried_at,
            )
        except ValueError:
            continue

        places.append(place)

    return places