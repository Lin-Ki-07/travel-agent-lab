// 把后端 map_days 转为地图覆盖物的描述。不在前端重新排序，也不计算路线或耗时。
import type { MapDay, MapStop } from './types'

export interface MarkerSpec {
  order: number
  name: string
  position: [number, number]
}

export interface DayOverlaySpec {
  markers: MarkerSpec[]
  // 示意线坐标，顺序与后端 line.positions 一致；[经度, 纬度]
  path: [number, number][]
  label: string
}

export function isValidPosition(value: unknown): value is [number, number] {
  if (!Array.isArray(value) || value.length !== 2) return false
  const [lng, lat] = value
  return (
    typeof lng === 'number' &&
    typeof lat === 'number' &&
    Number.isFinite(lng) &&
    Number.isFinite(lat) &&
    lng >= -180 && lng <= 180 &&
    lat >= -90 && lat <= 90
  )
}

// 标记按 stops.order 排序后绘制；坐标无效的点跳过（后端契约保证有效，这里是防御）。
export function buildOverlaySpec(day: MapDay): DayOverlaySpec {
  const markers: MarkerSpec[] = [...day.stops]
    .sort((a: MapStop, b: MapStop) => a.order - b.order)
    .filter((stop) => isValidPosition(stop.position))
    .map((stop) => ({ order: stop.order, name: stop.name, position: stop.position }))

  const path = day.line.positions.filter(isValidPosition)

  return { markers, path, label: day.line.label }
}

// 选中的日期索引，越界时回退到第一天；没有任何天时返回 0。
export function clampDayIndex(index: number, dayCount: number): number {
  if (dayCount <= 0) return 0
  if (!Number.isInteger(index) || index < 0) return 0
  return Math.min(index, dayCount - 1)
}
