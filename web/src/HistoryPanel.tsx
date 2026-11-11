import type { CreatePlanResponse } from './api'

interface HistoryPanelProps {
  plans: CreatePlanResponse[]
  savedIds: ReadonlySet<string>
  selectedId: string | null
  onSelect: (planId: string) => void
  onNewChat: () => void
}

// 参考 Codex 侧栏：顶部“新聊天”，下方每一项是一个行程对话，点击即进入。
export default function HistoryPanel({
  plans,
  savedIds,
  selectedId,
  onSelect,
  onNewChat,
}: HistoryPanelProps) {
  return (
    <div className="history">
      <button
        type="button"
        className={selectedId === null ? 'new-chat-button active' : 'new-chat-button'}
        onClick={onNewChat}
      >
        ＋ 新聊天
      </button>

      {plans.length === 0 ? (
        <p className="muted history-empty">还没有行程。在右侧表单生成后会出现在这里。</p>
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
    </div>
  )
}
