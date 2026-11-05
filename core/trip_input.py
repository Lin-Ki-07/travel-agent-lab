from datetime import date

from core.trip_models import TripRequest

def parse_trip_request(raw: dict[str, str]) -> TripRequest:
    """把命令行收集的文本字段转换为旅行请求。"""
    destination = raw.get("destination", "").strip()
    start_text = raw.get("start_date", "").strip()
    days_text = raw.get("days", "").strip()
    end_text = raw.get("end_date", "").strip()

    if not destination:
        raise ValueError("请提供目的地")
    if not start_text:
        raise ValueError("请提供出发日期，格式为 YYYY-MM-DD")
    if bool(days_text) == bool(end_text):
        raise ValueError("旅行天数和结束日期必须且只能填写一项")
    
    try:
        start_date = date.fromisoformat(start_text)
    except ValueError as exc:
        raise ValueError("出发日期格式或日期无效，应为 YYYY-MM-DD") from exc
    
    if days_text:
        try:
            days = int(days_text)
        except ValueError as exc:
            raise ValueError("旅行天数必须是整数") from exc
    else:
        try:
            end_date = date.fromisoformat(end_text)
        except ValueError as exc:
            raise ValueError("结束日期格式或日期无效，应为 YYYY-MM-DD") from exc
        days = (end_date - start_date).days + 1

    travelers_text = raw.get("travelers", "").strip()
    budget_text = raw.get("budget_cny", "").strip()

    try:
        travelers = int(travelers_text) if travelers_text else 1
        budget_cny = int(budget_text) if budget_text else None
    except ValueError as exc:
        raise ValueError("同行人数和预算必须是整数") from exc

    preferences = [
        item.strip()
        for item in raw.get("preferences", "").split(",")
        if item.strip()
    ]

    return TripRequest(
        destination=destination,
        start_date=start_date,
        days=days,
        travelers=travelers,
        budget_cny=budget_cny,
        preferences=preferences,
    )