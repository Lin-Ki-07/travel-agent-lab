import { useRef, type PointerEvent } from 'react'

interface ResizeHandleProps {
  label: string
  onDragStart: () => void
  // dx 为相对拖动开始时的水平位移（像素）。
  onDrag: (dx: number) => void
}

// 三栏之间的竖向分隔条。使用指针捕获，拖动时不需要全局监听。
export default function ResizeHandle({ label, onDragStart, onDrag }: ResizeHandleProps) {
  const startX = useRef<number | null>(null)

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    startX.current = event.clientX
    event.currentTarget.setPointerCapture(event.pointerId)
    onDragStart()
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (startX.current === null) return
    onDrag(event.clientX - startX.current)
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    startX.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  return (
    <div
      className="resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    />
  )
}
