import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  createPlan,
  deletePlan,
  getPreferences,
  getPlan,
  listSavedPlans,
  parseRequest,
  PlanApiError,
  savePlan,
  updatePlanDay,
  type CreatePlanResponse,
  type EditDayRequest,
  type SavedPlanSummary,
} from './api'
import ChatComposer from './ChatComposer'
import HistoryPanel from './HistoryPanel'
import PlanResultView from './PlanResultView'
import MapPanel from './MapPanel'
import NewChatView from './NewChatView'
import ResizeHandle from './ResizeHandle'
import { findReplacementTargets } from './editIntent'
import { formatParseReply, mergeParsedFields, missingTripFields, summarizeTripFields, toRequestBody, validateTripForm, type TripFormValues } from './tripRequest'

type Notice = { kind: 'success' | 'error'; text: string } | null

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  planCard?: boolean
  pending?: boolean
}

interface Chat {
  id: string
  title: string
  titleSource: 'auto' | 'manual'
  plan: CreatePlanResponse | null
  messages: ChatMessage[]
  draft: string
  parsing: boolean
  formOpen: boolean
  prefill: TripFormValues | null
  formKey: number
}

function createChat(): Chat {
  return{
    id: crypto.randomUUID(),
    title: '新的旅游规划',
    titleSource: 'auto',
    plan: null,
    messages: [],
    draft: '',
    parsing: false,
    formOpen: false,
    prefill: null,
    formKey: 0,
  }
}

type Theme = 'light' | 'dark'

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem('travel-agent-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    // 浏览器禁用本地存储时，仍可在当前页面切换主题。
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// 三栏宽度限制（像素）。中间栏为自适应剩余空间，并保证不小于 CENTER_MIN。
const LEFT_MIN = 160
const LEFT_MAX = 420
const RIGHT_MIN = 240
const RIGHT_MAX = 800
const CENTER_MIN = 320
const HANDLE_WIDTH = 6

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

// 对话先拥有独立 ID，生成行程后再关联后端 plan_id。
// 聊天状态只在当前页面内存中；刷新后只从后端恢复已保存行程。
export default function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [chats, setChats] = useState<Chat[]>(() => [createChat()])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [savedPlans, setSavedPlans] = useState<SavedPlanSummary[]>([])
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(() => readIdSet('travel-agent-pinned'))
  const [archivedIds, setArchivedIds] = useState<Set<string>>(() => readIdSet('travel-agent-archived'))
  const [defaultPreferences, setDefaultPreferences] = useState<string[]>([])
  const [preferencesLoaded, setPreferencesLoaded] = useState(false)
  const [openingPlanId, setOpeningPlanId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState(chats[0].id)
  const [saving, setSaving] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(420)
  const widthsAtDragStart = useRef({ left: 240, right: 420 })
  const sendingChats = useRef(new Set<string>())

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('travel-agent-theme', theme)
    } catch {
      // 存储不可用不影响当前页面的主题。
    }
  }, [theme])

  useEffect(() => {
    try {
      localStorage.setItem('travel-agent-pinned', JSON.stringify([...pinnedIds]))
      localStorage.setItem('travel-agent-archived', JSON.stringify([...archivedIds]))
    } catch { /* 存储不可用时仅在当前页面保留。 */ }
  }, [pinnedIds, archivedIds])

  const currentChat = chats.find((chat) => chat.id === selectedId)!
  const selected = currentChat.plan
  const isSaved = selected !== null && savedIds.has(selected.plan_id)
  useEffect(() => {
    let cancelled = false

    listSavedPlans()
      .then((result) => {
        if (!cancelled) setSavedPlans(result.plans)
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setNotice({
            kind: 'error',
            text: `读取已保存行程列表失败：${errorText(error, '请稍后刷新页面。')}`,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getPreferences()
      .then((result) => {
        if (!cancelled) {
          setDefaultPreferences(result.preferences)
          setPreferencesLoaded(true)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setNotice({
            kind: 'error',
            text: `读取默认偏好失败：${errorText(error, '请稍后刷新页面。')}`,
          })
        }
      })
    return () => { cancelled = true }
  }, [])
  function updateChat(id: string, changes: Partial<Chat>) {
    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== id) return chat

        const next = { ...chat, ...changes }
        const destination =
          changes.plan?.itinerary.request.destination ??
          changes.prefill?.destination

        if (next.titleSource === 'auto' && destination?.trim()) {
          next.title = `${destination.trim()}旅游攻略`
        }

        return next
      }),
    )
  }

  function handleNewChat() {
    setNotice(null)
    const chat = createChat()
    setChats((prev) => [chat, ...prev])
    setSelectedId(chat.id)
  }

  function handleGenerated(chatId: string, result: CreatePlanResponse) {
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, plan: result, messages: [...chat.messages, { role: 'assistant', text: '', planCard: true }] }
      : chat))
  }

  function handleSelect(planId: string) {
    setNotice(null)
    setSelectedId(planId)
  }

  async function handleOpenSaved(planId: string) {
    if (openingPlanId !== null) return

    setOpeningPlanId(planId)
    setNotice(null)
    try {
      const result = await getPlan(planId)
      const existing = chats.find((chat) => chat.plan?.plan_id === planId)

      if (existing) {
        updateChat(existing.id, { plan: result })
        setSelectedId(existing.id)
      } else {
        const chat = createChat()
        chat.plan = result
        chat.title = `${result.itinerary.request.destination}旅游攻略`
        setChats((prev) => [chat, ...prev])
        setSelectedId(chat.id)
      }
      setSavedIds((prev) => new Set(prev).add(planId))
    } catch (error) {
      setNotice({
        kind: 'error',
        text: `重新打开行程失败：${errorText(error, '请稍后重试。')}`,
      })
    } finally {
      setOpeningPlanId(null)
    }
  }

  function handleRename(chatId: string, title: string) {
    const trimmedTitle = title.trim()
    if (!trimmedTitle) return

    updateChat(chatId, {
      title: trimmedTitle,
      titleSource: 'manual',
    })
  }

  async function handleDeleteArchived(id: string, title: string, planId: string | null) {
    if (deletingId || !window.confirm(`永久删除“${title}”？已保存的行程记录也会从本地数据库删除，且无法恢复。`)) return
    setDeletingId(id)
    try {
      if (planId) await deletePlan(planId)
      const removedChatIds = chats.filter((chat) => chat.id === id || chat.plan?.plan_id === id).map((chat) => chat.id)
      const remaining = chats.filter((chat) => !removedChatIds.includes(chat.id))
      const nextChats = remaining.length ? remaining : [createChat()]
      setChats(nextChats)
      if (removedChatIds.includes(selectedId)) {
        setSelectedId(nextChats[0].id)
      }
      if (planId) {
        setSavedPlans((prev) => prev.filter((plan) => plan.plan_id !== planId))
        setSavedIds((prev) => { const next = new Set(prev); next.delete(planId); return next })
      }
      setPinnedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
      setArchivedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
      setNotice({ kind: 'success', text: `已永久删除“${title}”。` })
    } catch (error) {
      setNotice({ kind: 'error', text: `删除失败：${errorText(error, '请稍后重试。')}` })
    } finally {
      setDeletingId(null)
    }
  }

  function appendMessages(key: string, added: ChatMessage[]) {
    setChats((prev) => prev.map((chat) => chat.id === key
      ? { ...chat, messages: [...chat.messages, ...added] }
      : chat))
  }

  function removePendingMessage(chatId: string) {
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, messages: chat.messages.filter((message) => !message.pending) }
      : chat))
  }

  async function handleSend(text: string) {
    const chatId = currentChat.id
    if (sendingChats.current.has(chatId)) return
    updateChat(chatId, { draft: '' })

    // 已生成行程：先定位明确提出要替换的活动，暂不修改行程。
    if (selected) {
      const targets = findReplacementTargets(text, selected.itinerary)
      let reply = '这是已生成的行程。要规划新的行程，请点击左侧“＋ 新聊天”。'
      if (targets) {
        if (targets.length === 1) {
          const target = targets[0]
          reply = `我找到了第 ${target.dayNumber} 天的“${target.placeName}”（第 ${target.activityIndex + 1} 项）。你想替换这个地点。接下来可以提供候选地点并在地图上预览；现在行程尚未修改。`
        } else if (targets.length > 1) {
          reply = `“${targets[0].placeName}”在行程中出现多次：${targets.map((target) => `第 ${target.dayNumber} 天第 ${target.activityIndex + 1} 项`).join('、')}。请指出要替换哪一项；现在行程尚未修改。`
        } else {
          reply = '我还无法确定你想替换的地点。请直接说出行程中的地点名称，例如“我不想去太平府”；现在行程尚未修改。'
        }
      }
      appendMessages(chatId, [{ role: 'user', text }, { role: 'assistant', text: reply }])
      return
    }

    // 每次只解析本条消息，再与当前聊天已识别的字段合并；缺失项留在对话中追问。
    appendMessages(chatId, [{ role: 'user', text }])
    sendingChats.current.add(chatId)
    updateChat(chatId, { parsing: true })
    try {
      const result = await parseRequest(text)
      const merged = mergeParsedFields(currentChat.prefill, result.fields)
      const missing = missingTripFields(merged)
      const issues = Object.values(validateTripForm(merged))
      updateChat(chatId, { prefill: merged, formKey: currentChat.formKey + 1 })
      if (missing.length || issues.length) {
        appendMessages(chatId, [{
          role: 'assistant',
          text: formatParseReply({ summary: summarizeTripFields(merged), missing, issues: missing.length ? [] : issues }),
        }])
      } else {
        appendMessages(chatId, [{ role: 'assistant', text: '信息已齐全，正在生成行程…', pending: true }])
        const plan = await createPlan(toRequestBody(merged))
        removePendingMessage(chatId)
        handleGenerated(chatId, plan)
      }
    } catch (error) {
      removePendingMessage(chatId)
      appendMessages(chatId, [
        {
          role: 'assistant',
          text: `处理失败：${errorText(error, '请稍后重试。')} 已识别的信息保留在表单中。`,
        },
      ])
    } finally {
      sendingChats.current.delete(chatId)
      updateChat(chatId, { parsing: false })
    }
  }

  async function handleSave() {
    if (!selected || saving || isSaved) return
    setSaving(true)
    setNotice(null)
    try {
      await savePlan(selected.plan_id)
      setSavedIds((prev) => new Set(prev).add(selected.plan_id))
      setNotice({ kind: 'success', text: '行程已保存；刷新页面后可在左侧重新打开。' })
      try {
        const result = await listSavedPlans()
        setSavedPlans(result.plans)
      } catch {
        setNotice({ kind: 'success', text: '行程已保存；列表暂未刷新，可刷新页面后重新打开。' })
      }
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '保存失败，请稍后重试。') })
    } finally {
      setSaving(false)
    }
  }

  async function handleEditDay(dayNumber: number, body: EditDayRequest) {
    if (!selected || !isSaved || savingEdit) return

    setSavingEdit(true)
    setNotice(null)
    try {
      const updated = await updatePlanDay(selected.plan_id, dayNumber, body)
      updateChat(currentChat.id, { plan: updated })
      setNotice({ kind: 'success', text: `第 ${dayNumber} 天已更新，地图已同步。` })
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '编辑失败，原行程已保留。') })
      throw error
    } finally {
      setSavingEdit(false)
    }
  }

  function beginDrag() {
    widthsAtDragStart.current = { left: leftWidth, right: rightWidth }
  }

  // 左分隔条：向右拖动增加左栏宽度。
  function dragLeft(dx: number) {
    setLeftWidth(clamp(widthsAtDragStart.current.left + dx, LEFT_MIN, LEFT_MAX))
  }

  // 右分隔条：向左拖动增加地图栏宽度。
  function dragRight(dx: number) {
    setRightWidth(clamp(widthsAtDragStart.current.right - dx, RIGHT_MIN, RIGHT_MAX))
  }

  const gridColumns = `${leftWidth}px ${HANDLE_WIDTH}px minmax(${CENTER_MIN}px, 1fr) ${HANDLE_WIDTH}px ${rightWidth}px`

  return (
    <div className="layout" style={{ gridTemplateColumns: gridColumns }}>
      <aside className="pane pane-history" aria-label="对话列表">
        <HistoryPanel
          chats={chats}
          savedPlans={savedPlans}
          selectedId={selectedId}
          onSelect={handleSelect}
          onOpenSaved={handleOpenSaved}
          onNewChat={handleNewChat}
          onRename={handleRename}
          pinnedIds={pinnedIds}
          archivedIds={archivedIds}
          onTogglePin={(id) => setPinnedIds((current) => toggleId(current, id))}
          onToggleArchive={(id) => setArchivedIds((current) => toggleId(current, id))}
          onDeleteArchived={handleDeleteArchived}
          deletingId={deletingId}
          theme={theme}
          onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
          defaultPreferences={defaultPreferences}
          preferencesLoaded={preferencesLoaded}
          onPreferencesSaved={setDefaultPreferences}
        />
      </aside>

      <ResizeHandle label="调整左栏宽度" onDragStart={beginDrag} onDrag={dragLeft} />

      <main className="pane chat-pane" aria-label="对话">
        <div className="chat-scroll">
          {notice && !selected && (
            <div
              className={notice.kind === 'error' ? 'banner banner-error' : 'banner banner-success'}
              role={notice.kind === 'error' ? 'alert' : 'status'}
            >
              {notice.text}
            </div>
          )}

          {chats.filter((chat) => !chat.plan).map((chat) => (
            <div key={chat.id} hidden={chat.id !== selectedId}>
              <NewChatView
                defaultPreferences={defaultPreferences}
                preferencesLoaded={preferencesLoaded}
                formOpen={chat.formOpen}
                onFormOpenChange={(open) => updateChat(chat.id, { formOpen: open })}
                prefill={chat.prefill}
                formKey={chat.formKey}
                onGenerated={(result) => handleGenerated(chat.id, result)}
              />
            </div>
          ))}

          {currentChat.messages.map((message, index) => (
            message.planCard && selected ? (
              <PlanResultView
                key={`${selected.plan_id}-${index}`}
                plan={selected}
                notice={notice}
                isSaved={isSaved}
                saving={saving}
                savingEdit={savingEdit}
                onSave={handleSave}
                onEditDay={handleEditDay}
              />
            ) : (
              <div key={index} className={`chat-bubble ${message.role}`}>
                {message.text}
              </div>
            )
          ))}
          {selected && !currentChat.messages.some((message) => message.planCard) && (
            <PlanResultView
              key={selected.plan_id}
              plan={selected}
              notice={notice}
              isSaved={isSaved}
              saving={saving}
              savingEdit={savingEdit}
              onSave={handleSave}
              onEditDay={handleEditDay}
            />
          )}
        </div>

        <div className="chat-dock">
          <ChatComposer
            draft={currentChat.draft}
            onDraftChange={(draft) => updateChat(currentChat.id, { draft })}
            onSend={handleSend}
            disabled={currentChat.parsing}
            placeholder={currentChat.parsing ? '正在解析需求…' : undefined}
          />
        </div>
      </main>

      <ResizeHandle label="调整地图栏宽度" onDragStart={beginDrag} onDrag={dragRight} />

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        <MapPanel key={selected?.plan_id ?? 'empty'} days={selected?.map_days ?? []} />
      </section>
    </div>
  )
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof PlanApiError) return error.message
  return fallback
}

function readIdSet(key: string): Set<string> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    return new Set(Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string') : [])
  } catch { return new Set() }
}

function toggleId(current: ReadonlySet<string>, id: string): Set<string> {
  const next = new Set(current)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}
