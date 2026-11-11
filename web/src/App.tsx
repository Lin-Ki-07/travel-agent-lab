import { useState } from 'react'
import './App.css'
import { getPlan, PlanApiError, savePlan, type CreatePlanResponse } from './api'
import ChatComposer from './ChatComposer'
import HistoryPanel from './HistoryPanel'
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import NewChatView from './NewChatView'

type Notice = { kind: 'success' | 'error'; text: string } | null

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

const NEW_CHAT_KEY = '__new__'

// 一个对话对应一个行程。selectedId 为 null 时显示“新聊天”。
// 所有状态只在当前页面内存中，刷新页面或重启后端都会失效；不做编辑、账号或跨重启持久化。
export default function App() {
  const [plans, setPlans] = useState<CreatePlanResponse[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingById, setLoadingById] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState('')
  // 每个对话各自保存消息，切换对话时不串内容。
  const [messagesByChat, setMessagesByChat] = useState<Record<string, ChatMessage[]>>({})

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

  function handleSend(text: string) {
    setDraft('')
    const reply = selected
      ? '这是已生成的行程。要规划新的行程，请点击左侧“＋ 新聊天”。'
      : '直接用文字规划暂未接入后端。我已为你展开“旅行需求”表单，请在表单中填写后生成。'
    setMessagesByChat((prev) => ({
      ...prev,
      [chatKey]: [
        ...(prev[chatKey] ?? []),
        { role: 'user', text },
        { role: 'assistant', text: reply },
      ],
    }))
    if (!selected) setFormOpen(true)
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

  async function handleLoadById(planId: string) {
    setLoadingById(true)
    setNotice(null)
    try {
      const plan = await getPlan(planId)
      // 后端只允许读取已保存的行程，因此读取成功即表示已保存。
      setSavedIds((prev) => new Set(prev).add(plan.plan_id))
      upsertPlan(plan)
      setNotice({ kind: 'success', text: '已读取已保存的行程。' })
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '读取失败，请稍后重试。') })
    } finally {
      setLoadingById(false)
    }
  }

  return (
    <div className="layout">
      <aside className="pane pane-history" aria-label="对话列表">
        <HistoryPanel
          plans={plans}
          savedIds={savedIds}
          selectedId={selectedId}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
        />
      </aside>

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
              loadingById={loadingById}
              onGenerated={handleGenerated}
              onLoadById={handleLoadById}
            />
          )}

          {messages.map((message, index) => (
            <div key={index} className={`chat-bubble ${message.role}`}>
              {message.text}
            </div>
          ))}
        </div>

        <div className="chat-dock">
          <ChatComposer draft={draft} onDraftChange={setDraft} onSend={handleSend} />
        </div>
      </main>

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
