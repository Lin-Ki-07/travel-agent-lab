from core.trip_models import Itinerary


def format_itinerary(trip: Itinerary) -> str:
    """将已校验的逐日行程格式化为命令行文本。"""
    place_map = {place.place_id: place for place in trip.places}
    lines = [
        f"{trip.request.destination} {trip.request.days} 天游玩行程",
        f"同行人数：{trip.request.travelers}",
        "预算口径：人民币，全程所有同行者合计；金额仅为估算。",
    ]

    if trip.request.budget_cny is not None:
        lines.append(f"用户预算：{trip.request.budget_cny} 元")

    for day in trip.daily_plans:
        lines.append(f"\n第 {day.day_number} 天｜{day.plan_date.isoformat()}")

        if day.weather.available:
            lines.append(
                f"天气预报：{day.weather.condition}，"
                f"{day.weather.min_temp_c}–{day.weather.max_temp_c}°C"
            )
        else:
            lines.append("天气预报：该日期暂无可用预报")

        lines.append(
            f"天气来源：{day.weather.source}；"
            f"查询时间：{day.weather.queried_at.isoformat()}"
        )

        for activity in day.activities:
            place = place_map[activity.place_id]
            lines.append(
                f"{activity.start_time.strftime('%H:%M')}–"
                f"{activity.end_time.strftime('%H:%M')} "
                f"{place.name}（{place.place_id}）：{activity.description}"
            )
            lines.append(
                f"  地点：{place.address}；"
                f"坐标：{place.longitude},{place.latitude}；"
                f"来源：{place.source}；查询时间：{place.queried_at.isoformat()}"
            )

        for segment in day.transport_segments:
            start = place_map[segment.from_place_id].name
            end = place_map[segment.to_place_id].name
            duration = (
                f"；估算耗时约 {segment.estimated_minutes} 分钟"
                if segment.estimated_minutes is not None
                else "；耗时未知"
            )
            lines.append(f"交通：{start} → {end}，{segment.mode}{duration}")

        if day.estimated_cost_cny is None:
            lines.append("当日费用：未知")
        else:
            lines.append(
                f"当日估算费用：{day.estimated_cost_cny} 元；"
                f"依据：{day.cost_basis}"
            )

    if trip.estimated_total_cny is None:
        lines.append("\n全程费用：未知")
    else:
        lines.append(f"\n全程估算费用：{trip.estimated_total_cny} 元")

    return "\n".join(lines)