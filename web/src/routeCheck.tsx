// 独立开发验收入口：固定模拟几何，不请求模型/路线接口，不写入行程。
import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import MapPanel from './MapPanel'
import ItineraryView from './ItineraryView'
import type { Itinerary, MapDay, MapSegment, Place } from './types'
import './App.css'

const timestamp = '2026-11-26T06:30:00+00:00'
const positions: [number, number][] = [[116.39, 39.9], [116.40, 39.91], [116.42, 39.90]]
const places: Place[] = positions.map(([longitude, latitude], i) => ({
  place_id: `mock-${i}`, name: `模拟地点${i + 1}`, address: '模拟数据',
  longitude, latitude, source: 'fixture', queried_at: timestamp,
}))
const parts = [
  { mode: 'walking', positions: [positions[0], [116.39, 39.91], positions[1]] as [number, number][] },
  { mode: 'driving', positions: [positions[1], [116.42, 39.91], positions[2]] as [number, number][] },
]
const segments: MapSegment[] = parts.map((part, i) => ({
  from_order: i + 1, to_order: i + 2, kind: 'route_snapshot', parts: [part],
  fallback_positions: [positions[i], positions[i + 1]],
}))
const days: MapDay[] = [
  { day_number: 1, plan_date: '2026-11-26', stops: places.map((p, i) => ({
    order: i + 1, place_id: p.place_id, name: p.name, position: positions[i],
  })), line: { kind: 'place_order_schematic', label: '', positions }, segments },
  { day_number: 2, plan_date: '2026-11-27', stops: places.map((p, i) => ({
    order: i + 1, place_id: p.place_id, name: p.name, position: positions[i],
  })), line: { kind: 'place_order_schematic', label: '', positions }, segments: [
    { ...segments[0], parts: [{ ...parts[0], mode: 'transit' }] },
    { ...segments[1], kind: 'place_order_schematic', parts: [] },
  ] },
]
const itinerary: Itinerary = {
  request: { destination: '模拟验收', start_date: '2026-11-26', days: 2, travelers: 1, budget_cny: null, preferences: [] },
  places, generated_at: timestamp, estimated_total_cny: null,
  daily_plans: days.map((day, dayIndex) => ({
    day_number: day.day_number, plan_date: day.plan_date,
    weather: { forecast_date: day.plan_date, condition: null, min_temp_c: null, max_temp_c: null,
      available: false, source: 'fixture', queried_at: timestamp },
    activities: places.map((p, i) => ({ place_id: p.place_id, description: '模拟活动',
      start_time: `${9 + i * 2}:00`, end_time: `${10 + i * 2}:00` })),
    transport_segments: segments.map((_, i) => ({
      from_place_id: places[i].place_id, to_place_id: places[i + 1].place_id,
      mode: i === 0 ? (dayIndex === 1 ? '公交' : '步行') : '驾车', estimated_minutes: dayIndex === 1 && i === 1 ? null : 3,
      route: dayIndex === 1 && i === 1
        ? { status: 'failed', source: 'amap', queried_at: timestamp, distance_meters: null,
          duration_seconds: null, parts: [], failure_reason: '模拟超时' }
        : { status: 'ok', source: 'amap', queried_at: timestamp, distance_meters: 1250,
          duration_seconds: 121, parts: day.segments![i].parts, failure_reason: null },
    })), estimated_cost_cny: null, cost_basis: null,
  })),
}
const candidate: Place = { ...places[0], place_id: 'candidate', name: '模拟候选', longitude: 116.405, latitude: 39.905 }

export function RouteCheck() {
  const [selectedId, setSelectedId] = useState<string>()
  return <main style={{ padding: 20 }}>
    <h1>模拟验收：几何不代表真实道路</h1>
    <p>第1天全成功，第2天公交与失败回退；仅加载普通高德底图，不调用路线接口。</p>
    <p role="status">候选选择：{selectedId ?? '未选择'}</p>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
      <ItineraryView itinerary={itinerary} editable={false} savingEdit={false} onEditDay={async () => {}} />
      <MapPanel days={days} preview={{ target: { dayNumber: 1, activityIndex: 0,
        placeId: places[0].place_id, placeName: places[0].name }, candidates: [candidate], selectedId }}
        onSelectCandidate={setSelectedId} />
    </div>
  </main>
}

if (import.meta.env.DEV) createRoot(document.getElementById('root')!).render(<RouteCheck />)
