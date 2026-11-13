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

interface Chat {
  id: string
  plan: CreatePlanResponse | null
  messages: ChatMessage[]
  draft: string
  parsing: boolean
  formOpen: boolean
  prefill: TripFormValues | null
  formKey: number
}

function createChat(): Chat {
  return {
    id: crypto.randomUUID(),
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
// 所有状态只在当前页面内存中，刷新页面或重启后端都会失效；不做编辑、账号或跨重启持久化。
export default function App() {
  const [chats, setChats] = useState<Chat[]>(() => [createChat()])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState(chats[0].id)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(420)
  const widthsAtDragStart = useRef({ left: 240, right: 420 })

  const currentChat = chats.find((chat) => chat.id === selectedId)!
  const selected = currentChat.plan
  const isSaved = selected !== null && savedIds.has(selected.plan_id)
  function updateChat(id: string, changes: Partial<Chat>) {
    setChats((prev) => prev.map((chat) => chat.id === id ? { ...chat, ...changes } : chat))
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
          chats={chats}
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
          ) : null}

          {chats.filter((chat) => !chat.plan).map((chat) => (
            <div key={chat.id} hidden={chat.id !== selectedId}>
              <NewChatView
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
