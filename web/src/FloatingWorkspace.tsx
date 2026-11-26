import { useRef, useState, type PointerEvent, type ReactNode } from 'react'

export default function FloatingWorkspace({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [offset, setOffset] = useState<number | null>(null)
  const sheet = useRef<HTMLDivElement>(null)
  const gesture = useRef<{ y: number; start: number; max: number } | null>(null)

  function start(event: PointerEvent<HTMLButtonElement>) {
    if (event.button !== 0) return
    const max = Math.max(0, (sheet.current?.clientHeight ?? 0) - 44)
    gesture.current = { y: event.clientY, start: collapsed ? max : 0, max }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function finish(event: PointerEvent<HTMLButtonElement>, cancelled = false) {
    const drag = gesture.current
    if (!drag) return
    const dy = event.clientY - drag.y
    if (!cancelled && Math.abs(dy) > 6) {
      setCollapsed(Math.abs(dy) > 48 ? dy > 0 : drag.start + dy > drag.max / 2)
    }
    gesture.current = null
    setOffset(null)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }

  return (
    <div ref={sheet} className={`floating-workspace${collapsed ? ' is-collapsed' : ''}${offset !== null ? ' is-dragging' : ''}`}
      style={offset !== null ? { transform: `translateY(${offset}px)` } : undefined}>
      <button type="button" className="workspace-grip" aria-label={collapsed ? '展开聊天面板' : '收起聊天面板'}
        aria-expanded={!collapsed} aria-controls="workspace-content" title="上下拖动，或点击展开 / 收起"
        onPointerDown={start}
        onPointerMove={(event) => {
          const drag = gesture.current
          if (drag) setOffset(Math.min(drag.max, Math.max(0, drag.start + event.clientY - drag.y)))
        }}
        onPointerUp={(event) => {
          const click = gesture.current && Math.abs(event.clientY - gesture.current.y) <= 6
          finish(event)
          if (click) setCollapsed((value) => !value)
        }}
        onPointerCancel={(event) => finish(event, true)}
        onLostPointerCapture={() => { gesture.current = null; setOffset(null) }}
        onClick={(event) => { if (event.detail === 0) setCollapsed((value) => !value) }}
        onKeyDown={(event) => {
          if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
            event.preventDefault()
            setCollapsed(event.key === 'ArrowDown')
          }
        }}>
        <span />
      </button>
      <div id="workspace-content" className="workspace-content" inert={collapsed}>{children}</div>
    </div>
  )
}
