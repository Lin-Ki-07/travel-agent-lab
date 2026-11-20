import { useRef, useState } from 'react'
import type { CreatePlanResponse, SavedPlanSummary } from './api'
import PreferencesEditor from './PreferencesEditor'

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
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  defaultPreferences: string[]
  preferencesLoaded: boolean
  onPreferencesSaved: (preferences: string[]) => void
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
  theme,
  onToggleTheme,
  defaultPreferences,
  preferencesLoaded,
  onPreferencesSaved,
}: HistoryPanelProps) {
  const [menu, setMenu] = useState<ContextMenu | null>(null)
  const [bottomPanel, setBottomPanel] = useState<'archive' | 'preferences' | null>(null)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const openPlanIds = new Set(chats.flatMap((chat) => chat.plan ? [chat.plan.plan_id] : []))
  const entries = [
    ...chats.map((chat) => ({ id: chat.plan?.plan_id ?? chat.id, chatId: chat.id, title: chat.title, planId: null as string | null })),
    ...savedPlans.filter((plan) => !openPlanIds.has(plan.plan_id)).map((plan) => ({
      id: plan.plan_id, chatId: null as string | null, planId: plan.plan_id, title: `${plan.destination}旅游攻略`,
    })),
  ]
  const ordered = [...entries].sort((a, b) => Number(pinnedIds.has(b.id)) - Number(pinnedIds.has(a.id)))
  const archivedEntries = entries.filter((entry) => archivedIds.has(entry.id))

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
      <div className="history-main">
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

      </div>

      <div className="history-bottom">
        {bottomPanel && (
          <div className="history-popover" role="region" aria-label={bottomPanel === 'archive' ? '已归档聊天' : '默认旅行偏好'}>
            <div className="history-popover-heading">
              <strong>{bottomPanel === 'archive' ? '已归档聊天' : '默认旅行偏好'}</strong>
              <button type="button" aria-label="关闭面板" onClick={() => setBottomPanel(null)}>×</button>
            </div>
            {bottomPanel === 'archive' ? archivedEntries.length ? <ul className="history-list">{archivedEntries.map((entry) => (
            <li key={entry.id} className="history-item">
              <button type="button" className="history-row" onClick={() => {
                if (entry.chatId) onSelect(entry.chatId)
                else onOpenSaved(entry.planId!)
                setBottomPanel(null)
              }}>{entry.title}</button>
              <span className="history-actions"><button type="button" title="取消归档" aria-label={`取消归档${entry.title}`} onClick={() => onToggleArchive(entry.id)}><ArchiveIcon restore /></button></span>
            </li>
          ))}</ul> : <p className="muted">暂无已归档聊天。</p> : preferencesLoaded ? (
              <PreferencesEditor key={defaultPreferences.join('\u0000')} preferences={defaultPreferences} onSaved={onPreferencesSaved} />
            ) : <p className="muted">正在读取默认偏好…</p>}
          </div>
        )}
        <div className="history-bottom-actions">
          <button type="button" title={theme === 'dark' ? '切换到白天模式' : '切换到黑夜模式'} aria-label={theme === 'dark' ? '切换到白天模式' : '切换到黑夜模式'} onClick={onToggleTheme}>
            {theme === 'dark' ? <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg> : <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5Z"/></svg>}
          </button>
          <button type="button" title="归档" aria-label="查看归档" aria-expanded={bottomPanel === 'archive'} onClick={() => setBottomPanel((current) => current === 'archive' ? null : 'archive')}><ArchiveIcon /></button>
          <button type="button" title="默认旅行偏好" aria-label="编辑默认旅行偏好" aria-expanded={bottomPanel === 'preferences'} onClick={() => setBottomPanel((current) => current === 'preferences' ? null : 'preferences')}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 17h16M9 4v6M15 14v6"/><circle cx="9" cy="7" r="2"/><circle cx="15" cy="17" r="2"/></svg></button>
        </div>
        </div>

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
