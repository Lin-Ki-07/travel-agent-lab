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
  const route = segment.route
  if (route?.status === 'failed') return '该段路线不可用'
  if (route?.status === 'ok' && route.duration_seconds !== null) {
    const distance = route.distance_meters
    const distanceText = distance === null ? '' : distance < 1000
      ? ` · 约 ${distance} 米`
      : ` · 约 ${Number((distance / 1000).toFixed(1))} 公里`
    return `预计 ${Math.ceil(route.duration_seconds / 60)} 分钟${distanceText}`
  }
  return '该段路线未查询'
}

export function formatRouteDetails(segment: TransportSegment): string {
  const route = segment.route
  if (!route || route.status !== 'ok') return ''
  const source = route.source === 'amap' ? '高德' : route.source
  const date = new Date(route.queried_at)
  const timestamp = Number.isNaN(date.getTime()) ? '未知' : new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
  return `来源：${source}；查询时间：${timestamp}（北京时间）`
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


export function formatTransportMode(mode: string): string {
  return ['打车', '出租车', 'taxi'].includes(mode.trim().toLowerCase()) ? '驾车' : mode
}
