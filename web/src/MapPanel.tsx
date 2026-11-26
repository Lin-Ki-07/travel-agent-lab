import { useEffect, useRef, useState } from 'react'
import { loadAmap, readAmapConfig, type AMapMap, type AMapNamespace } from './amapLoader'
import { buildOverlaySpec, clampDayIndex } from './mapModel'
import type { MapDay, Place } from './types'
import type { ActivityTarget } from './editIntent'

interface MapPanelProps {
  // 没有行程时传入空数组：地图仍显示（全国视野），但不绘制标记和示意线。
  days: MapDay[]
  background?: boolean
  selectedDayIndex?: number
  onDayIndexChange?: (index: number) => void
  preview?: { target: ActivityTarget; candidates: Place[]; selectedId?: string }
  onSelectCandidate?: (placeId: string) => void
}

type MapStatus =
  | { kind: 'no-key' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready' }

const DEFAULT_CENTER: [number, number] = [104.1, 35.9]

export default function MapPanel({ days, preview, onSelectCandidate, background = false, selectedDayIndex, onDayIndexChange }: MapPanelProps) {
  const [dayIndex, setDayIndex] = useState(0)
  // 没有 Key 时直接进入 no-key 状态，不加载脚本，effect 内无需同步 setState。
  const [status, setStatus] = useState<MapStatus>(() =>
    readAmapConfig() ? { kind: 'loading' } : { kind: 'no-key' },
  )
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<AMapMap | null>(null)
  const amapRef = useRef<AMapNamespace | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)

  const safeIndex = clampDayIndex(selectedDayIndex ?? dayIndex, days.length)
  const currentDay = days[safeIndex] as MapDay | undefined
  const lineLabel = currentDay ? buildOverlaySpec(currentDay).label : ''

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
      .then(() => {
        // 三栏可拖动，容器尺寸会变化；高德默认只监听窗口变化，这里让地图跟随容器重新布局。
        if (cancelled || !containerRef.current || typeof ResizeObserver === 'undefined') return
        resizeObserverRef.current = new ResizeObserver(() => mapRef.current?.resize())
        resizeObserverRef.current.observe(containerRef.current)
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
      resizeObserverRef.current?.disconnect()
      resizeObserverRef.current = null
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
      const pin = document.createElement('div')
      pin.className = 'numbered-map-pin'
      if (preview?.target.dayNumber === currentDay.day_number && marker.order === preview.target.activityIndex + 1 && marker.placeId === preview.target.placeId) {
        pin.classList.add('numbered-map-pin-target')
      }
      const number = document.createElement('span')
      number.textContent = String(marker.order)
      pin.appendChild(number)
      overlays.push(
        new AMap.Marker({
          position: marker.position,
          title: marker.name,
          content: pin,
          offset: new AMap.Pixel(-16, -42),
        }),
      )
    })

    if (preview?.target.dayNumber === currentDay.day_number) {
      preview.candidates.forEach((place) => {
        const pin = document.createElement('button')
        pin.type = 'button'
        pin.className = `numbered-map-pin candidate-map-pin${preview.selectedId === place.place_id ? ' selected' : ''}`
        pin.setAttribute('aria-label', `选择候选地点 ${place.name}`)
        pin.addEventListener('click', () => onSelectCandidate?.(place.place_id))
        overlays.push(new AMap.Marker({
          position: [place.longitude, place.latitude],
          title: place.name,
          content: pin,
          offset: new AMap.Pixel(-16, -42),
        }))
      })
    }

    spec.lines.forEach((line) => {
      overlays.push(
        new AMap.Polyline({
          path: line.path,
          strokeColor: line.color,
          strokeWeight: 4,
          strokeOpacity: 0.8,
          strokeStyle: line.dashed ? 'dashed' : 'solid',
          lineJoin: 'round',
        }),
      )
    })

    if (overlays.length > 0) {
      map.add(overlays)
      map.setFitView(overlays, false, [40, 40, 40, 40])
    }
  }, [currentDay, status.kind, preview, onSelectCandidate])

  const overlayMessage =
    status.kind === 'no-key'
      ? '未配置高德 JS API Key，地图暂不显示。请在 web/.env.local 中填写 VITE_AMAP_JS_KEY 后重启开发服务器。'
      : status.kind === 'error'
        ? status.message
        : status.kind === 'loading'
          ? '地图加载中…'
          : null

  return (
    <div className={background ? "map-panel map-panel-background" : "map-panel"}>
      {!background && days.length > 0 && (
        <>
          <div className="day-tabs" role="tablist" aria-label="按日查看地图">
            {days.map((day, index) => (
              <button
                key={day.day_number}
                type="button"
                role="tab"
                aria-selected={index === safeIndex}
                className={index === safeIndex ? 'day-tab active' : 'day-tab'}
                onClick={() => { setDayIndex(index); onDayIndexChange?.(index) }}
              >
                第 {day.day_number} 天
              </button>
            ))}
          </div>
          {currentDay && <p className="muted">{currentDay.plan_date}</p>}
          {preview && currentDay?.day_number === preview.target.dayNumber && <p className="muted">红色：待替换地点　绿色：候选地点；点击候选只预览，不保存。</p>}
          {preview && currentDay?.day_number !== preview.target.dayNumber && <p className="muted">候选预览在第 {preview.target.dayNumber} 天，切换到该日可查看。</p>}
        </>
      )}

      <div className="map-canvas-wrap">
        <div ref={containerRef} className="map-canvas" aria-label="高德地图" />
        {overlayMessage && <p className="map-overlay muted">{overlayMessage}</p>}
      </div>

      {!background && (days.length === 0 ? (
        <p className="muted">选择或生成一个行程后，这里按日期显示地点与示意线。</p>
      ) : (
        currentDay && (
          <>
            {lineLabel && <p className="line-note">{lineLabel}</p>}
            <ol className="stop-list">
              {currentDay.stops.map((stop) => (
                <li key={`${stop.order}-${stop.place_id}`}>
                  <span className="stop-order">{stop.order}</span> {stop.name}
                </li>
              ))}
            </ol>
          </>
        )
      ))}
    </div>
  )
}
