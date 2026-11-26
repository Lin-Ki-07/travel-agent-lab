import { useEffect, useRef, useState, type ReactNode, type PointerEvent } from 'react'

type Position = { x: number; y: number; width: number; height: number }
function constrain(position: Position): Position {
  const width = Math.min(position.width, window.innerWidth)
  const height = Math.min(position.height, window.innerHeight)
  return { width, height, x: Math.max(0, Math.min(position.x, window.innerWidth - width)),
    y: Math.max(0, Math.min(position.y, window.innerHeight - height)) }
}

export default function DraggableDetails({ children, onDetach, onDock }: { children: ReactNode; onDetach: () => void; onDock: () => void }) {
  const anchor = useRef<HTMLDivElement>(null)
  const [preview, setPreview] = useState<{ position: Position; dock: boolean } | null>(null)
  const panel = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<Position | null>(null)
  const drag = useRef<{ x: number; y: number; origin: Position } | null>(null)
  const [moving, setMoving] = useState(false)

  useEffect(() => {
    const resize = () => setPosition((current) => current ? constrain(current) : null)
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  function getSnap(next: Position) {
    const rect = anchor.current?.getBoundingClientRect()
    const left = anchor.current?.parentElement?.querySelector('.floating-workspace')
    if (rect && !left?.classList.contains('is-collapsed') &&
      Math.abs(next.x - rect.x) <= 36 && Math.abs(next.y - rect.y) <= 36 &&
      rect.right <= window.innerWidth && rect.bottom <= window.innerHeight) {
      return { position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }, dock: true }
    }
    const snapped = { ...next }
    let hit = false
    if (next.x <= 24) { snapped.x = 0; hit = true }
    else if (window.innerWidth - next.x - next.width <= 24) { snapped.x = window.innerWidth - next.width; hit = true }
    if (next.y <= 24) { snapped.y = 0; hit = true }
    else if (window.innerHeight - next.y - next.height <= 24) { snapped.y = window.innerHeight - next.height; hit = true }
    return hit ? { position: snapped, dock: false } : null
  }

  function move(event: PointerEvent<HTMLButtonElement>) {
    const current = drag.current
    if (!current) return null
    const dx = event.clientX - current.x
    const dy = event.clientY - current.y
    if (!moving && Math.hypot(dx, dy) < 6) return null
    return constrain({ ...current.origin, x: current.origin.x + dx, y: current.origin.y + dy })
  }

  return (
    <>
    <div ref={anchor} className="details-dock-anchor" aria-hidden="true" />
    {preview && <div className="details-snap-preview" aria-hidden="true" style={{ left: preview.position.x, top: preview.position.y, width: preview.position.width, height: preview.position.height }} />}
    <div ref={panel} className={`floating-workspace details-workspace${position ? ' is-detached' : ''}${moving ? ' is-moving' : ''}`}
      style={position ? { position: 'fixed', left: position.x, top: position.y, width: position.width, height: position.height } : undefined}>
      <button type="button" className="workspace-grip details-grip" aria-label="移动行程详情面板"
        title="拖动移动；方向键微调位置"
        onPointerDown={(event) => {
          if (event.button !== 0 || !panel.current) return
          const rect = panel.current.getBoundingClientRect()
          drag.current = { x: event.clientX, y: event.clientY,
            origin: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } }
          event.currentTarget.setPointerCapture(event.pointerId)
        }}
        onPointerMove={(event) => {
          const next = move(event)
          if (!next) return
          onDetach()
          setMoving(true)
          setPosition(next)
          setPreview(getSnap(next))
        }}
        onPointerUp={(event) => {
          const next = move(event)
          const snap = next ? getSnap(next) : null
          if (snap?.dock) { setPosition(null); onDock() }
          else if (snap) setPosition(snap.position)
          else if (next) setPosition(next)
          setPreview(null)
          drag.current = null
          setMoving(false)
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
        }}
        onPointerCancel={() => { drag.current = null; setMoving(false); setPreview(null) }}
        onLostPointerCapture={() => { drag.current = null; setMoving(false); setPreview(null) }}
        onKeyDown={(event) => {
          if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key) || !panel.current) return
          event.preventDefault()
          const rect = panel.current.getBoundingClientRect()
          const step = event.shiftKey ? 40 : 10
          onDetach()
          setPosition(constrain({ x: rect.x + (event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0),
            y: rect.y + (event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0), width: rect.width, height: rect.height }))
        }}><span /></button>
      {children}
    </div>
    </>
  )
}
