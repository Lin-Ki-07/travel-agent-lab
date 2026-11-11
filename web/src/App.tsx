import { useState } from 'react'
import './App.css'
import { getPlan, PlanApiError, savePlan, type CreatePlanResponse } from './api'
import HistoryPanel from './HistoryPanel'
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import TripForm from './TripForm'

type Notice = { kind: 'success' | 'error'; text: string } | null

// 阶段 5：表单 + 逐日行程 + 地图 + 历史记录 + 保存与按 plan_id 读取。
// 所有状态只在当前页面内存中，刷新页面或重启后端都会失效；不做编辑、账号或跨重启持久化。
export default function App() {
  const [plans, setPlans] = useState<CreatePlanResponse[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice>(null)

  const selected = plans.find((plan) => plan.plan_id === selectedId) ?? null
  const isSaved = selected !== null && savedIds.has(selected.plan_id)

  function upsertPlan(plan: CreatePlanResponse) {
    setPlans((prev) => [plan, ...prev.filter((item) => item.plan_id !== plan.plan_id)])
    setSelectedId(plan.plan_id)
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
    setLoadingId(planId)
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
      setLoadingId(null)
    }
  }

  return (
    <div className="layout">
      <aside className="pane pane-history" aria-label="历史记录">
        <h2>历史记录</h2>
        <HistoryPanel
          plans={plans}
          savedIds={savedIds}
          selectedId={selectedId}
          loadingId={loadingId}
          onSelect={handleSelect}
          onLoadById={handleLoadById}
        />
      </aside>

      <main className="pane pane-chat" aria-label="对话">
        <h2>Travel Agent Lab</h2>
        <p className="muted">填写需求后生成逐日行程。</p>
        <TripForm onGenerated={handleGenerated} />

        {notice && (
          <div
            className={notice.kind === 'error' ? 'banner banner-error' : 'banner banner-success'}
            role={notice.kind === 'error' ? 'alert' : 'status'}
          >
            {notice.text}
          </div>
        )}

        {selected && (
          <>
            <div className="plan-toolbar">
              <p className="muted">
                plan_id：{selected.plan_id}（{isSaved ? '已保存' : '未保存，仅本次进程内有效'}）
              </p>
              <button type="button" onClick={handleSave} disabled={saving || isSaved}>
                {isSaved ? '已保存' : saving ? '保存中…' : '保存当前行程'}
              </button>
            </div>
            <ItineraryView itinerary={selected.itinerary} />
          </>
        )}
      </main>

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        {selected ? (
          <MapPanel key={selected.plan_id} days={selected.map_days} />
        ) : (
          <p className="muted">生成或读取行程后，这里按日期显示地点与示意线。</p>
        )}
      </section>
    </div>
  )
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof PlanApiError) return error.message
  return fallback
}
