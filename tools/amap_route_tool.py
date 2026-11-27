"""高德路径规划 2.0 适配层，不调用模型。"""

import os
from datetime import date, datetime, time, timezone

import requests

from core.trip_models import Place, RoutePart, RouteSnapshot


ENDPOINTS = {
    "walking": "https://restapi.amap.com/v5/direction/walking",
    "driving": "https://restapi.amap.com/v5/direction/driving",
    "transit": "https://restapi.amap.com/v5/direction/transit/integrated",
}


def _positive_integer(value: object) -> int:
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError("无效距离或耗时")


def _part(mode: str, polyline: object) -> RoutePart:
    if not isinstance(polyline, str):
        raise ValueError("缺少路线点串")
    # 按经纬度对解析；不猜测缺失坐标，也不连接起终点伪造道路。
    positions = [[float(v) for v in pair.split(",")] for pair in polyline.split(";")]
    return RoutePart(mode, positions)


def _parts(plan: dict, mode: str) -> list[RoutePart]:
    if mode != "transit":
        return [_part(mode, step["polyline"]) for step in plan["steps"]]
    result = []
    for segment in plan["segments"]:
        # 未支持的铁路/出租车几何不能悄悄遗漏，否则会产生不完整路线。
        if segment.get("railway") or segment.get("taxi"):
            raise ValueError("暂不支持铁路或出租车混合方案")
        walking = segment.get("walking") or {}
        for step in walking.get("steps", []):
            result.append(_part("walking", step["polyline"]))
        bus = segment.get("bus") or {}
        lines = bus.get("buslines") or []
        if lines:
            # 同一分段中的 buslines 为备选线路，不顺次拼接。
            result.append(_part("transit", lines[0]["polyline"]))
        if not walking.get("steps") and not lines:
            raise ValueError("公交分段缺少可用几何")
    return result


def _has_subway(plan: dict) -> bool:
    # 官方v3公交字段定义（v5引用）：type为“地铁线路”。仅检查实际采用的首条busline。
    return any(
        lines and lines[0].get("type") == "地铁线路"
        for segment in plan["segments"]
        for lines in [(segment.get("bus") or {}).get("buslines") or []]
    )


def query_amap_route(
    origin: Place,
    destination: Place,
    mode: str,
    *,
    api_key: str | None = None,
    origin_citycode: str | None = None,
    destination_citycode: str | None = None,
    departure_date: date | None = None,
    departure_time: time | None = None,
) -> RouteSnapshot:
    """公交在可用方案中按耗时及地铁偏好选择，道路取首条；单次请求，不重试。"""
    queried_at = datetime.now(timezone.utc)

    def failed(reason: str, kind: str = "unavailable") -> RouteSnapshot:
        return RouteSnapshot("failed", "amap", queried_at, failure_reason=reason, failure_kind=kind)

    if mode not in ENDPOINTS:
        return failed("不支持的交通方式")
    key = api_key if api_key is not None else os.getenv("AMAP_API_KEY")
    if not key or not key.strip():
        return failed("未配置高德 Web 服务 Key", "blocked")
    params = {
        "key": key,
        "origin": f"{origin.longitude:.6f},{origin.latitude:.6f}",
        "destination": f"{destination.longitude:.6f},{destination.latitude:.6f}",
        "show_fields": "cost,polyline",
        "output": "json",
    }
    if mode == "transit":
        if any(not isinstance(code, str) or not code.isascii() or not code.isdecimal()
               for code in (origin_citycode, destination_citycode)):
            return failed("公交查询缺少有效城市编码", "blocked")
        params.update(city1=origin_citycode, city2=destination_citycode, AlternativeRoute="5")
        if departure_date is not None:
            params["date"] = departure_date.isoformat()
        if departure_time is not None:
            params["time"] = departure_time.strftime("%H-%M")
    try:
        response = requests.get(ENDPOINTS[mode], params=params, timeout=(5, 10))
        response.raise_for_status()
        data = response.json()
    except requests.Timeout:
        return failed("高德路线请求超时")
    except (requests.RequestException, ValueError):
        # 不传播异常文本、URL、原始响应或 info，避免密钥出现在错误中。
        return failed("高德路线请求或响应解析失败")
    if not isinstance(data, dict):
        return failed("高德路线响应格式不合法")
    if data.get("status") != "1":
        code = data.get("infocode")
        safe_code = code if isinstance(code, str) and len(code) == 5 and code.isascii() and code.isdecimal() else "未知"
        return failed(f"高德路线服务拒绝请求（错误码：{safe_code}）",
                      "no_route" if safe_code in {"20011", "20800", "20801", "20802", "20803"} else "blocked")
    try:
        plans = data["route"]["transits" if mode == "transit" else "paths"]
        if not isinstance(plans, list):
            raise ValueError("方案必须是列表")
        if not plans:
            return failed("高德未返回可用路线", "no_route")
        # 只在同一公交响应内选方案，不为损坏方案增加网络请求。
        candidates = []
        for plan in (plans if mode == "transit" else plans[:1]):
            try:
                snapshot = RouteSnapshot(
                    "ok", "amap", queried_at,
                    distance_meters=_positive_integer(plan["distance"]),
                    duration_seconds=_positive_integer(plan["cost"]["duration"]),
                    parts=_parts(plan, mode),
                )
                if mode != "transit":
                    return snapshot
                candidates.append((snapshot, _has_subway(plan)))
            except (KeyError, TypeError, ValueError, IndexError, OverflowError, AttributeError):
                continue
        if candidates:
            fastest = min(candidates, key=lambda candidate: candidate[0].duration_seconds)[0]
            subways = [route for route, has_subway in candidates if has_subway
                       and route.duration_seconds - fastest.duration_seconds <= 900
                       and route.duration_seconds * 4 <= fastest.duration_seconds * 5]
            return min(subways, key=lambda route: route.duration_seconds) if subways else fastest
    except (KeyError, TypeError, ValueError, IndexError, OverflowError, AttributeError):
        pass
    return failed("高德路线方案缺少有效距离、耗时或完整几何", "unavailable")
