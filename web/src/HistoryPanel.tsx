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

// 参考 Codex 侧栏：扁平列表，点击即进入，选中行高亮；读取入口收在底部折叠区。
export default function HistoryPanel({
  plans,
  savedIds,
  selectedId,
  loadingId,
  onSelect,
  onLoadById,
}: HistoryPanelProps) {
  const [showLoad, setShowLoad] = useState(false)
  const [idInput, setIdInput] = useState('')

  function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const planId = idInput.trim()
    if (!planId || loadingId) return
    onLoadById(planId)
  }

  return (
    <div className="history">
      <div className="history-heading">最近</div>

      {plans.length === 0 ? (
        <p className="muted history-empty">还没有行程。生成后会出现在这里。</p>
      ) : (
        <ul className="history-list">
          {plans.map((plan) => {
            const { request } = plan.itinerary
            const selected = plan.plan_id === selectedId
            const saved = savedIds.has(plan.plan_id)
            return (
              <li key={plan.plan_id}>
                <button
                  type="button"
                  className={selected ? 'history-row active' : 'history-row'}
                  onClick={() => onSelect(plan.plan_id)}
                  aria-current={selected ? 'true' : undefined}
                  title={`${request.destination} · ${request.start_date} · ${request.days} 天`}
                >
                  <span className="history-title">
                    {request.destination} · {request.days} 天
                  </span>
                  {saved && <span className="saved-dot" aria-label="已保存" title="已保存" />}
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <div className="history-footer">
        <button
          type="button"
          className="history-toggle"
          onClick={() => setShowLoad((value) => !value)}
          aria-expanded={showLoad}
        >
          {showLoad ? '收起读取' : '按 plan_id 读取'}
        </button>

        {showLoad && (
          <form className="load-by-id" onSubmit={handleLoad}>
            <input
              value={idInput}
              onChange={(e) => setIdInput(e.target.value)}
              placeholder="粘贴已保存行程的 plan_id"
              aria-label="plan_id"
            />
            <button type="submit" disabled={!idInput.trim() || loadingId !== null}>
              {loadingId ? '读取中…' : '读取'}
            </button>
          </form>
        )}

        <p className="muted history-note">仅本次进程内有效，重启后失效。</p>
      </div>
    </div>
  )
}
