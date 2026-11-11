import { useState, type FormEvent } from 'react'
import type { CreatePlanResponse } from './api'

interface HistoryPanelProps {
  plans: CreatePlanResponse[]
  savedIds: ReadonlySet<string>
  selectedId: string | null
  loadingId: string | null
  onSelect: (planId: string) => void
  onLoadById: (planId: string) => void
}

export default function HistoryPanel({
  plans,
  savedIds,
  selectedId,
  loadingId,
  onSelect,
  onLoadById,
}: HistoryPanelProps) {
  const [idInput, setIdInput] = useState('')

  function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const planId = idInput.trim()
    if (!planId || loadingId) return
    onLoadById(planId)
  }

  return (
    <div className="history">
      <p className="muted">仅本次进程内有效，重启后失效。</p>

      {plans.length === 0 ? (
        <p className="muted">还没有行程。生成后会出现在这里。</p>
      ) : (
        <ul className="history-list">
          {plans.map((plan) => {
            const { request } = plan.itinerary
            const selected = plan.plan_id === selectedId
            return (
              <li key={plan.plan_id}>
                <button
                  type="button"
                  className={selected ? 'history-item active' : 'history-item'}
                  onClick={() => onSelect(plan.plan_id)}
                  aria-current={selected ? 'true' : undefined}
                >
                  <strong>{request.destination}</strong>
                  <span className="muted">
                    {request.start_date} · {request.days} 天
                  </span>
                  <span className={savedIds.has(plan.plan_id) ? 'badge badge-saved' : 'badge'}>
                    {savedIds.has(plan.plan_id) ? '已保存' : '未保存'}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <form className="load-by-id" onSubmit={handleLoad}>
        <label>
          <span>按 plan_id 读取已保存行程</span>
          <input
            value={idInput}
            onChange={(e) => setIdInput(e.target.value)}
            placeholder="粘贴 plan_id"
          />
        </label>
        <button type="submit" disabled={!idInput.trim() || loadingId !== null}>
          {loadingId ? '读取中…' : '读取'}
        </button>
      </form>
    </div>
  )
}
