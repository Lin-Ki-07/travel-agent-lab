import { useEffect, useRef, useState, type ReactNode } from 'react'

type Position = { x: number; y: number; width: number; height: number }
function constrain(position: Position): Position {
  const width = Math.min(position.width, window.innerWidth)
  const height = Math.min(position.height, window.innerHeight)
  return { width, height, x: Math.max(0, Math.min(position.x, window.innerWidth - width)),
    y: Math.max(0, Math.min(position.y, window.innerHeight - height)) }
}

export default function DraggableDetails({ children, onDetach }: { children: ReactNode; onDetach: () => void }) {
  const panel = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<Position | null>(null)
  const drag = useRef<{ x: number; y: number; origin: Position } | null>(null)
  const [moving, setMoving] = useState(false)

  useEffect(() => {
    const resize = () => setPosition((current) => current ? constrain(current) : null)
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  return (
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
          const current = drag.current
          if (!current) return
          const dx = event.clientX - current.x
          const dy = event.clientY - current.y
          if (!moving && Math.hypot(dx, dy) < 6) return
          onDetach()
          setMoving(true)
          setPosition(constrain({ ...current.origin, x: current.origin.x + dx, y: current.origin.y + dy }))
        }}
        onPointerUp={(event) => {
          drag.current = null
          setMoving(false)
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
        }}
        onPointerCancel={() => { drag.current = null; setMoving(false) }}
        onLostPointerCapture={() => { drag.current = null; setMoving(false) }}
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
  )
}
