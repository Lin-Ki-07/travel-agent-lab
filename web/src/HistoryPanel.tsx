import { useRef, useState } from 'react'
import type { CreatePlanResponse, SavedPlanSummary } from './api'

interface HistoryPanelProps {
  chats: { id: string; title: string; plan: CreatePlanResponse | null }[]
  selectedId: string | null
  onSelect: (chatId: string) => void
  onNewChat: () => void
  onRename: (chatId: string, title: string) => void
  savedPlans: SavedPlanSummary[]
  onOpenSaved: (planId: string) => void
  pinnedIds: ReadonlySet<string>
  archivedIds: ReadonlySet<string>
  onTogglePin: (id: string) => void
  onToggleArchive: (id: string) => void
}

interface ContextMenu {
  chatId: string
  x: number
  y: number
}

function PinIcon({ filled }: { filled: boolean }) {
  return <svg viewBox="0 0 24 24" width="16" height="16" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m16 3 5 5-3 1-3 5-2 2-5-5 2-2 5-3z"/><path d="m8 16-5 5"/></svg>
}

function ArchiveIcon({ restore = false }: { restore?: boolean }) {
  return <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8"/>{restore ? <path d="m9 15 3-3 3 3M12 12v6"/> : <path d="M10 13h4"/>}</svg>
}

export default function HistoryPanel({
  chats,
  savedPlans,
  selectedId,
  onSelect,
  onOpenSaved,
  onNewChat,
  onRename,
  pinnedIds,
  archivedIds,
  onTogglePin,
  onToggleArchive,
}: HistoryPanelProps) {
  const [menu, setMenu] = useState<ContextMenu | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const openPlanIds = new Set(chats.flatMap((chat) => chat.plan ? [chat.plan.plan_id] : []))
  const entries = [
    ...chats.map((chat) => ({ id: chat.plan?.plan_id ?? chat.id, chatId: chat.id, title: chat.title, planId: null as string | null })),
    ...savedPlans.filter((plan) => !openPlanIds.has(plan.plan_id)).map((plan) => ({
      id: plan.plan_id, chatId: null as string | null, planId: plan.plan_id, title: `${plan.destination}旅游攻略`,
    })),
  ]
  const ordered = [...entries].sort((a, b) => Number(pinnedIds.has(b.id)) - Number(pinnedIds.has(a.id)))

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

      <ul className="history-list">
          {ordered.filter((entry) => !archivedIds.has(entry.id)).map((entry) => {
            const selected = entry.chatId === selectedId
            return (
              <li key={entry.id} className="history-item">
                <button
                  type="button"
                  className={selected ? 'history-row active' : 'history-row'}
                  onClick={() => entry.chatId ? onSelect(entry.chatId) : onOpenSaved(entry.planId!)}
                  onContextMenu={(event) => {
                    if (!entry.chatId) return
                    event.preventDefault()
                    triggerRef.current = event.currentTarget
                    setMenu({
                      chatId: entry.chatId,
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
                  aria-expanded={menu?.chatId === entry.chatId}
                  title={entry.title}
                >
                  <span className="history-title">{entry.title}</span>
                </button>
                <span className="history-actions">
                  <button type="button" title={pinnedIds.has(entry.id) ? '取消置顶' : '置顶'} aria-label={`${pinnedIds.has(entry.id) ? '取消置顶' : '置顶'}${entry.title}`} onClick={() => onTogglePin(entry.id)}><PinIcon filled={pinnedIds.has(entry.id)} /></button>
                  <button type="button" title="归档" aria-label={`归档${entry.title}`} onClick={() => onToggleArchive(entry.id)}><ArchiveIcon /></button>
                </span>
              </li>
            )
          })}
      </ul>

      {entries.some((entry) => archivedIds.has(entry.id)) && (
        <div className="archived-chats">
          <button type="button" className="archived-toggle" onClick={() => setShowArchived((value) => !value)} aria-expanded={showArchived}>归档 {showArchived ? '▾' : '▸'}</button>
          {showArchived && <ul className="history-list">{entries.filter((entry) => archivedIds.has(entry.id)).map((entry) => (
            <li key={entry.id} className="history-item">
              <button type="button" className="history-row" onClick={() => entry.chatId ? onSelect(entry.chatId) : onOpenSaved(entry.planId!)}>{entry.title}</button>
              <span className="history-actions"><button type="button" title="取消归档" aria-label={`取消归档${entry.title}`} onClick={() => onToggleArchive(entry.id)}><ArchiveIcon restore /></button></span>
            </li>
          ))}</ul>}
        </div>
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
