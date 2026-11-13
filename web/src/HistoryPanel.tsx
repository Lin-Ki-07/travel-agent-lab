import type { CreatePlanResponse } from './api'

interface HistoryPanelProps {
  chats: { id: string; plan: CreatePlanResponse | null }[]
  savedIds: ReadonlySet<string>
  selectedId: string | null
  onSelect: (planId: string) => void
  onNewChat: () => void
}

// 参考 Codex 侧栏：顶部“新聊天”，下方每一项是一个行程对话，点击即进入。
export default function HistoryPanel({
  chats,
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

      {chats.length === 0 ? (
        <p className="muted history-empty">还没有对话。点击“＋ 新聊天”开始。</p>
      ) : (
        <ul className="history-list">
          {chats.map((chat) => {
            const request = chat.plan?.itinerary.request
            const selected = chat.id === selectedId
            const saved = chat.plan !== null && savedIds.has(chat.plan.plan_id)
            const title = request ? `${request.destination} · ${request.days} 天` : '新聊天'
            return (
              <li key={chat.id}>
                <button
                  type="button"
                  className={selected ? 'history-row active' : 'history-row'}
                  onClick={() => onSelect(chat.id)}
                  aria-current={selected ? 'true' : undefined}
                  title={request ? `${request.destination} · ${request.start_date} · ${request.days} 天` : title}
                >
                  <span className="history-title">
                    {title}
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
