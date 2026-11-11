import { useEffect, useRef, useState } from 'react'
import { loadAmap, readAmapConfig, type AMapMap, type AMapNamespace } from './amapLoader'
import { buildOverlaySpec, clampDayIndex } from './mapModel'
import type { MapDay } from './types'

interface MapPanelProps {
  // 没有行程时传入空数组：地图仍显示（全国视野），但不绘制标记和示意线。
  days: MapDay[]
}

type MapStatus =
  | { kind: 'no-key' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready' }

const DEFAULT_CENTER: [number, number] = [104.1, 35.9]

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
  const currentDay = days[safeIndex] as MapDay | undefined

  // 初始化地图（只做一次）。即使还没有行程，也先显示地图。
  useEffect(() => {
    const config = readAmapConfig()
    if (!config) return

    let cancelled = false
    loadAmap(config)
      .then((AMap) => {
        if (cancelled || !containerRef.current) return
        amapRef.current = AMap
        mapRef.current = new AMap.Map(containerRef.current, {
          zoom: 4,
          center: DEFAULT_CENTER,
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

  // 切换日期或数据时重绘覆盖物；没有行程时只清空。
  useEffect(() => {
    const AMap = amapRef.current
    const map = mapRef.current
    if (!AMap || !map) return

    map.clearMap()
    if (!currentDay) return

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

  const overlayMessage =
    status.kind === 'no-key'
      ? '未配置高德 JS API Key，地图暂不显示。请在 web/.env.local 中填写 VITE_AMAP_JS_KEY 后重启开发服务器。'
      : status.kind === 'error'
        ? status.message
        : status.kind === 'loading'
          ? '地图加载中…'
          : null

  return (
    <div className="map-panel">
      {days.length > 0 && (
        <>
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
          {currentDay && <p className="muted">{currentDay.plan_date}</p>}
        </>
      )}

      <div className="map-canvas-wrap">
        <div ref={containerRef} className="map-canvas" aria-label="高德地图" />
        {overlayMessage && <p className="map-overlay muted">{overlayMessage}</p>}
      </div>

      {days.length === 0 ? (
        <p className="muted">选择或生成一个行程后，这里按日期显示地点与示意线。</p>
      ) : (
        currentDay && (
          <>
            <p className="line-note">{currentDay.line.label}</p>
            <ol className="stop-list">
              {currentDay.stops.map((stop) => (
                <li key={`${stop.order}-${stop.place_id}`}>
                  <span className="stop-order">{stop.order}</span> {stop.name}
                </li>
              ))}
            </ol>
          </>
        )
      )}
    </div>
  )
}
