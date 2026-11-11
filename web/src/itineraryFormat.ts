// 展示用的纯函数。未知值一律显示为明确的“未知”文案，不编造数值。

import type { Activity, DailyPlan, Itinerary, Place, TransportSegment, WeatherSnapshot } from './types'

// "09:30:00" 或 "09:30" -> "09:30"
export function formatTime(value: string): string {
  return value.slice(0, 5)
}

export function formatTimeRange(activity: Activity): string {
  return `${formatTime(activity.start_time)}–${formatTime(activity.end_time)}`
}

export function placeNameById(places: Place[], placeId: string): string {
  return places.find((place) => place.place_id === placeId)?.name ?? '未知地点'
}

export function formatWeather(weather: WeatherSnapshot): string {
  if (!weather.available) return '暂无可用预报'
  return `${weather.condition ?? '—'}，${weather.min_temp_c}°C ～ ${weather.max_temp_c}°C`
}

export function formatCost(cost: number | null): string {
  return cost === null ? '费用未知' : `约 ¥${cost}`
}

export function formatSegmentDuration(segment: TransportSegment): string {
  return segment.estimated_minutes === null
    ? '耗时未知'
    : `约 ${segment.estimated_minutes} 分钟`
}

// 总费用为 null 时，无法判断是否符合预算。
export function budgetStatus(itinerary: Itinerary): string {
  const { estimated_total_cny: total } = itinerary
  const budget = itinerary.request.budget_cny
  if (total === null) return '总费用未知，无法判断是否符合预算'
  if (budget === null) return `预计总费用约 ¥${total}（未设置预算）`
  return total > budget
    ? `预计总费用约 ¥${total}，超出预算 ¥${budget}`
    : `预计总费用约 ¥${total}，预算 ¥${budget} 以内`
}

export function describeDay(day: DailyPlan): string {
  return `第 ${day.day_number} 天 · ${day.plan_date}`
}
