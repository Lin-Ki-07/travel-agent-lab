import { useRef, useState } from 'react'
import type { CreatePlanResponse, SavedPlanSummary } from './api'

interface HistoryPanelProps {
  chats: { id: string; title: string; plan: CreatePlanResponse | null }[]
  savedIds: ReadonlySet<string>
  selectedId: string | null
  onSelect: (chatId: string) => void
  onNewChat: () => void
  onRename: (chatId: string, title: string) => void
  savedPlans: SavedPlanSummary[]
  onOpenSaved: (planId: string) => void
}

interface ContextMenu {
  chatId: string
  x: number
  y: number
}

export default function HistoryPanel({
  chats,
  savedIds,
  savedPlans,
  selectedId,
  onSelect,
  onOpenSaved,
  onNewChat,
  onRename,
}: HistoryPanelProps) {
  const [menu, setMenu] = useState<ContextMenu | null>(null)
  const triggerRef = useRef<HTMLButtonElement | null>(null)

  function closeMenu() {
    setMenu(null)
    triggerRef.current?.focus()
  }

  function renameChat() {
    if (!menu) return

    const chat = chats.find((item) => item.id === menu.chatId)
    closeMenu()
    if (!chat) return

    const title = window.prompt('请输入新的聊天名称', chat.title)
    if (title?.trim()) {
      onRename(chat.id, title)
    }
  }

  return (
    <div className="history">
      <button
        type="button"
        className="new-chat-button"
        onClick={onNewChat}
      >
        ＋ 新聊天
      </button>

      <p className="muted history-section-title">已保存行程</p>
      {savedPlans.length === 0 ? (
        <p className="muted history-empty">暂无已保存行程。</p>
      ) : (
        <ul className="history-list">
          {savedPlans.map((plan) => (
            <li key={plan.plan_id}>
              <button
                type="button"
                className="history-row"
                onClick={() => onOpenSaved(plan.plan_id)}
                title={`${plan.destination} · ${plan.start_date} 起 ${plan.days} 天`}
              >
                <span className="history-title">
                  {plan.destination}旅游攻略 · {plan.start_date}
                </span>
                <span className="saved-dot" aria-label="已保存" title="已保存" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="muted history-section-title">当前页面聊天</p>

      {chats.length === 0 ? (
        <p className="muted history-empty">
          还没有对话。点击“＋ 新聊天”开始。
        </p>
      ) : (
        <ul className="history-list">
          {chats.map((chat) => {
            const selected = chat.id === selectedId
            const saved =
              chat.plan !== null && savedIds.has(chat.plan.plan_id)

            return (
              <li key={chat.id}>
                <button
                  type="button"
                  className={selected ? 'history-row active' : 'history-row'}
                  onClick={() => onSelect(chat.id)}
                  onContextMenu={(event) => {
                    event.preventDefault()
                    triggerRef.current = event.currentTarget
                    setMenu({
                      chatId: chat.id,
                      x: Math.max(
                        8,
                        Math.min(event.clientX, window.innerWidth - 188),
                      ),
                      y: Math.max(
                        8,
                        Math.min(event.clientY, window.innerHeight - 64),
                      ),
                    })
                  }}
                  aria-current={selected ? 'true' : undefined}
                  aria-haspopup="menu"
                  aria-expanded={menu?.chatId === chat.id}
                  title={chat.title}
                >
                  <span className="history-title">{chat.title}</span>
                  {saved && (
                    <span
                      className="saved-dot"
                      aria-label="已保存"
                      title="已保存"
                    />
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {menu && (
        <>
          <button
            type="button"
            className="chat-menu-backdrop"
            aria-label="关闭聊天菜单"
            onClick={closeMenu}
            onContextMenu={(event) => {
              event.preventDefault()
              closeMenu()
            }}
          />
          <div
            className="chat-context-menu"
            role="menu"
            aria-label="聊天操作"
            style={{ left: menu.x, top: menu.y }}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                event.preventDefault()
                closeMenu()
              }
            }}
          >
            <button
              type="button"
              role="menuitem"
              autoFocus
              onClick={renameChat}
            >
              重命名
            </button>
          </div>
        </>
      )}
    </div>
  )
}
