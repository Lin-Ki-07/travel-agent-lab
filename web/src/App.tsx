import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
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
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import PreferencesEditor from './PreferencesEditor'
import NewChatView from './NewChatView'
import ResizeHandle from './ResizeHandle'
import { formatParseReply, fromParsedFields, type TripFormValues } from './tripRequest'

type Notice = { kind: 'success' | 'error'; text: string } | null

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
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
  const [chats, setChats] = useState<Chat[]>(() => [createChat()])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [savedPlans, setSavedPlans] = useState<SavedPlanSummary[]>([])
  const [defaultPreferences, setDefaultPreferences] = useState<string[]>([])
  const [preferencesLoaded, setPreferencesLoaded] = useState(false)
  const [openingPlanId, setOpeningPlanId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState(chats[0].id)
  const [saving, setSaving] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(420)
  const widthsAtDragStart = useRef({ left: 240, right: 420 })

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
    updateChat(chatId, { plan: result })
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

  function appendMessages(key: string, added: ChatMessage[]) {
    setChats((prev) => prev.map((chat) => chat.id === key
      ? { ...chat, messages: [...chat.messages, ...added] }
      : chat))
  }

  async function handleSend(text: string) {
    const chatId = currentChat.id
    updateChat(chatId, { draft: '' })

    // 已生成的行程页面：不再解析，只提示如何开始新的规划。
    if (selected) {
      appendMessages(chatId, [
        { role: 'user', text },
        { role: 'assistant', text: '这是已生成的行程。要规划新的行程，请点击左侧“＋ 新聊天”。' },
      ])
      return
    }

    // 新聊天：调用后端解析需求，结果填入表单，由用户确认后再生成。
    appendMessages(chatId, [{ role: 'user', text }])
    updateChat(chatId, { parsing: true })
    try {
      const result = await parseRequest(text)
      updateChat(chatId, {
        prefill: fromParsedFields(result.fields),
        formKey: currentChat.formKey + 1,
        formOpen: true,
      })
      appendMessages(chatId, [{ role: 'assistant', text: formatParseReply(result) }])
    } catch (error) {
      updateChat(chatId, { formOpen: true })
      appendMessages(chatId, [
        {
          role: 'assistant',
          text: `需求解析失败：${errorText(error, '请稍后重试。')} 你可以直接在表单中填写。`,
        },
      ])
    } finally {
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
          savedIds={savedIds}
          savedPlans={savedPlans}
          selectedId={selectedId}
          onSelect={handleSelect}
          onOpenSaved={handleOpenSaved}
          onNewChat={handleNewChat}
          onRename={handleRename}
        />
        <p className="muted history-note">
          仅已保存行程可在刷新后重新打开；聊天消息、草稿和手动标题不会恢复。
        </p>
        {preferencesLoaded && (
          <PreferencesEditor
            key={defaultPreferences.join('\u0000')}
            preferences={defaultPreferences}
            onSaved={setDefaultPreferences}
          />
        )}
      </aside>

      <ResizeHandle label="调整左栏宽度" onDragStart={beginDrag} onDrag={dragLeft} />

      <main className="pane chat-pane" aria-label="对话">
        <div className="chat-scroll">
          {notice && (
            <div
              className={notice.kind === 'error' ? 'banner banner-error' : 'banner banner-success'}
              role={notice.kind === 'error' ? 'alert' : 'status'}
            >
              {notice.text}
            </div>
          )}

          {selected ? (
            <div className="new-chat">
              <div className="chat-bubble user">
                {selected.itinerary.request.destination} · {selected.itinerary.request.start_date} 起 ·{' '}
                {selected.itinerary.request.days} 天 · {selected.itinerary.request.travelers} 人
              </div>
              <div className="chat-bubble assistant">
                行程已生成。右侧可按天查看地图，下方为逐日安排。
              </div>
              <div className="plan-toolbar">
                <p className="muted">
                  plan_id：{selected.plan_id}（{isSaved ? '已保存' : '未保存，刷新页面后无法重新打开'}）
                </p>
                <button type="button" onClick={handleSave} disabled={saving || isSaved}>
                  {isSaved ? '已保存' : saving ? '保存中…' : '保存当前行程'}
                </button>
              </div>
              <ItineraryView
                itinerary={selected.itinerary}
                editable={isSaved}
                savingEdit={savingEdit}
                onEditDay={handleEditDay}
              />
            </div>
          ) : null}

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
            <div key={index} className={`chat-bubble ${message.role}`}>
              {message.text}
            </div>
          ))}
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
