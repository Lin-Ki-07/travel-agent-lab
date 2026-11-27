// 把后端 map_days 转为地图覆盖物的描述。不在前端重新排序，也不计算路线或耗时。
import type { MapDay, MapStop } from './types'

export interface MarkerSpec {
  order: number
  placeId: string
  name: string
  position: [number, number]
}

export interface DayOverlaySpec {
  markers: MarkerSpec[]
  lines: { path: [number, number][]; color: string; dashed: boolean }[]
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
    .map((stop) => ({ order: stop.order, placeId: stop.place_id, name: stop.name, position: stop.position }))

  const lines: DayOverlaySpec['lines'] = []
  const modes = new Set<string>()
  const validPath = (points: unknown): points is [number, number][] =>
    Array.isArray(points) && points.length >= 2 && points.every(isValidPosition)
  if (day.segments !== undefined) {
    for (const segment of day.segments) {
      const usable = segment.kind === 'route_snapshot' && Array.isArray(segment.parts) &&
        segment.parts.length > 0 && segment.parts.every((part) =>
          ['walking', 'driving', 'transit'].includes(part.mode) && validPath(part.positions))
      if (!usable) continue
      for (const part of segment.parts) {
        const style = part.mode === 'walking' ? { color: '#238636', name: '绿色：步行' }
          : part.mode === 'driving' ? { color: '#2a71d3', name: '蓝色：驾车' }
            : { color: '#8957b5', name: '紫色：公交' }
        lines.push({ path: part.positions, color: style.color, dashed: false })
        modes.add(style.name)
      }
    }
  }
  const label = lines.length === 0 ? '' : [
    ...modes, modes.size > 0 ? '实线为路线快照' : '',
  ].filter(Boolean).join('；')
  return { markers, lines, label }
}

// 选中的日期索引，越界时回退到第一天；没有任何天时返回 0。
export function clampDayIndex(index: number, dayCount: number): number {
  if (dayCount <= 0) return 0
  if (!Number.isInteger(index) || index < 0) return 0
  return Math.min(index, dayCount - 1)
}
