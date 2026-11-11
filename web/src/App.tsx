import { useRef, useState } from 'react'
import './App.css'
import { parseRequest, PlanApiError, savePlan, type CreatePlanResponse } from './api'
import ChatComposer from './ChatComposer'
import HistoryPanel from './HistoryPanel'
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import NewChatView from './NewChatView'
import ResizeHandle from './ResizeHandle'
import { formatParseReply, fromParsedFields, type TripFormValues } from './tripRequest'

type Notice = { kind: 'success' | 'error'; text: string } | null

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

const NEW_CHAT_KEY = '__new__'

// 三栏宽度限制（像素）。中间栏为自适应剩余空间，并保证不小于 CENTER_MIN。
const LEFT_MIN = 160
const LEFT_MAX = 420
const RIGHT_MIN = 240
const RIGHT_MAX = 800
const CENTER_MIN = 320
const HANDLE_WIDTH = 6

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

// 一个对话对应一个行程。selectedId 为 null 时显示“新聊天”。
// 所有状态只在当前页面内存中，刷新页面或重启后端都会失效；不做编辑、账号或跨重启持久化。
export default function App() {
  const [plans, setPlans] = useState<CreatePlanResponse[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [parsing, setParsing] = useState(false)
  // 自然语言解析结果填入表单；每次解析递增 formKey，使表单以新值重新挂载。
  const [prefill, setPrefill] = useState<TripFormValues | null>(null)
  const [formKey, setFormKey] = useState(0)
  // 每个对话各自保存消息，切换对话时不串内容。
  const [messagesByChat, setMessagesByChat] = useState<Record<string, ChatMessage[]>>({})
  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(420)
  const widthsAtDragStart = useRef({ left: 240, right: 420 })

  const selected = plans.find((plan) => plan.plan_id === selectedId) ?? null
  const isSaved = selected !== null && savedIds.has(selected.plan_id)
  const chatKey = selected ? selected.plan_id : NEW_CHAT_KEY
  const messages = messagesByChat[chatKey] ?? []

  function upsertPlan(plan: CreatePlanResponse) {
    setPlans((prev) => [plan, ...prev.filter((item) => item.plan_id !== plan.plan_id)])
    setSelectedId(plan.plan_id)
  }

  function handleNewChat() {
    setNotice(null)
    setSelectedId(null)
  }

  function handleGenerated(result: CreatePlanResponse) {
    setNotice(null)
    upsertPlan(result)
  }

  function handleSelect(planId: string) {
    setNotice(null)
    setSelectedId(planId)
  }

  function appendMessages(key: string, added: ChatMessage[]) {
    setMessagesByChat((prev) => ({ ...prev, [key]: [...(prev[key] ?? []), ...added] }))
  }

  async function handleSend(text: string) {
    setDraft('')

    // 已生成的行程页面：不再解析，只提示如何开始新的规划。
    if (selected) {
      appendMessages(chatKey, [
        { role: 'user', text },
        { role: 'assistant', text: '这是已生成的行程。要规划新的行程，请点击左侧“＋ 新聊天”。' },
      ])
      return
    }

    // 新聊天：调用后端解析需求，结果填入表单，由用户确认后再生成。
    appendMessages(NEW_CHAT_KEY, [{ role: 'user', text }])
    setParsing(true)
    try {
      const result = await parseRequest(text)
      setPrefill(fromParsedFields(result.fields))
      setFormKey((key) => key + 1)
      setFormOpen(true)
      appendMessages(NEW_CHAT_KEY, [{ role: 'assistant', text: formatParseReply(result) }])
    } catch (error) {
      setFormOpen(true)
      appendMessages(NEW_CHAT_KEY, [
        {
          role: 'assistant',
          text: `需求解析失败：${errorText(error, '请稍后重试。')} 你可以直接在表单中填写。`,
        },
      ])
    } finally {
      setParsing(false)
    }
  }

  async function handleSave() {
    if (!selected || saving || isSaved) return
    setSaving(true)
    setNotice(null)
    try {
      await savePlan(selected.plan_id)
      setSavedIds((prev) => new Set(prev).add(selected.plan_id))
      setNotice({ kind: 'success', text: '已保存。重启后端后该行程将无法再读取。' })
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '保存失败，请稍后重试。') })
    } finally {
      setSaving(false)
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
          plans={plans}
          savedIds={savedIds}
          selectedId={selectedId}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
        />
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
                  plan_id：{selected.plan_id}（{isSaved ? '已保存' : '未保存，仅本次进程内有效'}）
                </p>
                <button type="button" onClick={handleSave} disabled={saving || isSaved}>
                  {isSaved ? '已保存' : saving ? '保存中…' : '保存当前行程'}
                </button>
              </div>
              <ItineraryView itinerary={selected.itinerary} />
            </div>
          ) : (
            <NewChatView
              formOpen={formOpen}
              onFormOpenChange={setFormOpen}
              prefill={prefill}
              formKey={formKey}
              onGenerated={handleGenerated}
            />
          )}

          {messages.map((message, index) => (
            <div key={index} className={`chat-bubble ${message.role}`}>
              {message.text}
            </div>
          ))}
        </div>

        <div className="chat-dock">
          <ChatComposer
            draft={draft}
            onDraftChange={setDraft}
            onSend={handleSend}
            disabled={parsing}
            placeholder={parsing ? '正在解析需求…' : undefined}
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
