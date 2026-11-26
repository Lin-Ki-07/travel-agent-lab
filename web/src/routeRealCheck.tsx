// 只展示一次已授权查询的结果，不发起业务请求，不修改已保存行程。
import { createRoot } from 'react-dom/client'
import MapPanel from './MapPanel'
import type { MapDay, RouteSnapshot } from './types'
import result from '../route-check-real.json'
import './App.css'

const route = result.route as RouteSnapshot
const positions = [result.origin_position, result.destination_position] as [number, number][]
const day: MapDay = {
  day_number: 1, plan_date: route.queried_at.slice(0, 10),
  stops: [result.origin, result.destination].map((name, i) => ({
    order: i + 1, place_id: `check-${i}`, name, position: positions[i],
  })),
  line: { kind: 'place_order_schematic', label: '', positions },
  segments: [{ from_order: 1, to_order: 2,
    kind: route.status === 'ok' ? 'route_snapshot' : 'place_order_schematic',
    parts: route.parts, fallback_positions: positions }],
}

export function RealRouteCheck() {
  return <main style={{ padding: 20, maxWidth: 960, margin: 'auto' }}>
    <h1>{result.origin} → {result.destination} · 真实步行路线</h1>
    <p>高德查询快照：{route.distance_meters} 米，预计 {Math.ceil((route.duration_seconds ?? 0) / 60)} 分钟。仅展示已取得结果，不重新查询。</p>
    <MapPanel days={[day]} />
  </main>
}

if (import.meta.env.DEV) createRoot(document.getElementById('root')!).render(<RealRouteCheck />)
