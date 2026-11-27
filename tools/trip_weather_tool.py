from datetime import date, datetime, timedelta, timezone

import requests

from core.trip_models import WeatherSnapshot

def get_trip_weather(city: str, start_date: date, days: int) -> list[WeatherSnapshot]:
    """查询逐日预报；未被接口覆盖的日期保留为空快照。"""
    if not city.strip():
        raise ValueError("天气查询城市不能为空")
    if days < 1:
        raise ValueError("旅行天数必须大于等于 1")
    
    try:
        response = requests.get(
            f"https://wttr.in/{city.strip()}",
            params={"format": "j1"},
            timeout=(5, 10),
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise RuntimeError("天气服务请求超时") from exc
    except requests.ConnectionError as exc:
        raise RuntimeError("无法连接天气服务") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else response.status_code
        raise RuntimeError(f"天气服务返回 HTTP {status}") from exc
    except requests.RequestException as exc:
        raise RuntimeError("天气服务请求失败") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("天气响应不是有效 JSON") from exc

    if not isinstance(data, dict):
        raise RuntimeError("天气响应格式不合法：应为对象")

    forecasts = data.get("weather")
    if not isinstance(forecasts, list):
        raise RuntimeError("天气响应缺少逐日预报列表")
    
    by_date = {}
    for item in forecasts:
        if not isinstance(item, dict):
            continue
        try:
            forecast_date = date.fromisoformat(item["date"])
        except (KeyError, TypeError, ValueError):
            continue
        by_date[forecast_date] = item
    
    queried_at = datetime.now(timezone.utc)
    snapshots = []

    for offset in range(days):
        plan_date = start_date + timedelta(days=offset)
        item = by_date.get(plan_date)

        if item is None:
            snapshots.append(
                WeatherSnapshot(
                    forecast_date=plan_date,
                    condition=None,
                    min_temp_c=None,
                    max_temp_c=None,
                    available=False,
                    source="wttr.in",
                    queried_at=queried_at,
                )
            )
            continue

        try:
            min_temp = float(item["mintempC"])
            max_temp = float(item["maxtempC"])
            first_hour = item["hourly"][0]
            description = first_hour["weatherDesc"][0]["value"].strip()
            hour = first_hour.get("time", "0")
            condition = f"{hour} 时段预报：{description}"
            snapshots.append(
                WeatherSnapshot(
                    forecast_date=plan_date,
                    condition=condition,
                    min_temp_c=min_temp,
                    max_temp_c=max_temp,
                    available=True,
                    source="wttr.in",
                    queried_at=queried_at,
                )
            )
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise RuntimeError(
                f"{plan_date.isoformat()} 的天气预报字段不完整"
            ) from exc
        
    return snapshots
        
