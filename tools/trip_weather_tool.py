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
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("天气请求或响应解析失败") from exc
    
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
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"{plan_date.isoformat()} 的天气预报字段不完整"
            ) from exc
        
    return snapshots
        
