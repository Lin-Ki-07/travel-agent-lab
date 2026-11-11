import { useEffect, useRef, useState } from 'react'
import { loadAmap, readAmapConfig, type AMapMap, type AMapNamespace } from './amapLoader'
import { buildOverlaySpec, clampDayIndex } from './mapModel'
import type { MapDay } from './types'

interface MapPanelProps {
  days: MapDay[]
}

type MapStatus =
  | { kind: 'no-key' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready' }

export default function MapPanel({ days }: MapPanelProps) {
  const [dayIndex, setDayIndex] = useState(0)
  // 没有 Key 时直接进入 no-key 状态，不加载脚本，effect 内无需同步 setState。
  const [status, setStatus] = useState<MapStatus>(() =>
    readAmapConfig() ? { kind: 'loading' } : { kind: 'no-key' },
  )
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<AMapMap | null>(null)
  const amapRef = useRef<AMapNamespace | null>(null)

  const safeIndex = clampDayIndex(dayIndex, days.length)
  const currentDay = days[safeIndex]

  // 初始化地图（只做一次）。
  useEffect(() => {
    const config = readAmapConfig()
    if (!config) return

    let cancelled = false
    loadAmap(config)
      .then((AMap) => {
        if (cancelled || !containerRef.current) return
        amapRef.current = AMap
        mapRef.current = new AMap.Map(containerRef.current, {
          zoom: 12,
          viewMode: '2D',
        })
        setStatus({ kind: 'ready' })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setStatus({
          kind: 'error',
          message: error instanceof Error ? error.message : '地图加载失败。',
        })
      })

    return () => {
      cancelled = true
      mapRef.current?.destroy()
      mapRef.current = null
    }
  }, [])

  // 切换日期或数据时重绘覆盖物。
  useEffect(() => {
    const AMap = amapRef.current
    const map = mapRef.current
    if (!AMap || !map || !currentDay) return

    map.clearMap()

    const spec = buildOverlaySpec(currentDay)
    const overlays: unknown[] = []

    spec.markers.forEach((marker) => {
      overlays.push(
        new AMap.Marker({
          position: marker.position,
          title: marker.name,
          label: { content: String(marker.order), direction: 'top' },
        }),
      )
    })

    if (spec.path.length >= 2) {
      overlays.push(
        new AMap.Polyline({
          path: spec.path,
          strokeColor: '#2a71d3',
          strokeWeight: 4,
          strokeOpacity: 0.8,
          strokeStyle: 'dashed',
          lineJoin: 'round',
        }),
      )
    }

    if (overlays.length > 0) {
      map.add(overlays)
      map.setFitView(overlays, false, [40, 40, 40, 40])
    }
  }, [currentDay, status.kind])

  if (days.length === 0) {
    return <p className="muted">生成行程后，这里按日期显示地点与示意线。</p>
  }

  return (
    <div className="map-panel">
      <div className="day-tabs" role="tablist" aria-label="按日查看地图">
        {days.map((day, index) => (
          <button
            key={day.day_number}
            type="button"
            role="tab"
            aria-selected={index === safeIndex}
            className={index === safeIndex ? 'day-tab active' : 'day-tab'}
            onClick={() => setDayIndex(index)}
          >
            第 {day.day_number} 天
          </button>
        ))}
      </div>

      <p className="muted">{currentDay.plan_date}</p>

      {status.kind === 'ready' || status.kind === 'loading' ? (
        <div className="map-canvas-wrap">
          <div ref={containerRef} className="map-canvas" aria-label="高德地图" />
          {status.kind === 'loading' && <p className="muted">地图加载中…</p>}
        </div>
      ) : (
        <div className="banner banner-pending" role="status">
          {status.kind === 'no-key'
            ? '未配置高德 JS API Key，地图暂不显示。请在 web/.env.local 中填写 VITE_AMAP_JS_KEY 后重启开发服务器。'
            : status.message}
        </div>
      )}

      <p className="line-note">{currentDay.line.label}</p>

      <ol className="stop-list">
        {currentDay.stops.map((stop) => (
          <li key={`${stop.order}-${stop.place_id}`}>
            <span className="stop-order">{stop.order}</span> {stop.name}
          </li>
        ))}
      </ol>
    </div>
  )
}
