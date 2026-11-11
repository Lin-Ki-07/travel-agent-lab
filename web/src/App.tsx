import { useState } from 'react'
import './App.css'
import { getPlan, PlanApiError, savePlan, type CreatePlanResponse } from './api'
import HistoryPanel from './HistoryPanel'
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import NewChatView from './NewChatView'

type Notice = { kind: 'success' | 'error'; text: string } | null

// 一个对话对应一个行程。selectedId 为 null 时显示“新聊天”（表单）。
// 所有状态只在当前页面内存中，刷新页面或重启后端都会失效；不做编辑、账号或跨重启持久化。
export default function App() {
  const [plans, setPlans] = useState<CreatePlanResponse[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingById, setLoadingById] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)

  const selected = plans.find((plan) => plan.plan_id === selectedId) ?? null
  const isSaved = selected !== null && savedIds.has(selected.plan_id)

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

      <main className="pane pane-chat" aria-label="对话">
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
            loadingById={loadingById}
            onGenerated={handleGenerated}
            onLoadById={handleLoadById}
          />
        )}
      </main>

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        {selected ? (
          <MapPanel key={selected.plan_id} days={selected.map_days} />
        ) : (
          <p className="muted">生成或选择一个行程后，这里按日期显示地点与示意线。</p>
        )}
      </section>
    </div>
  )
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof PlanApiError) return error.message
  return fallback
}
