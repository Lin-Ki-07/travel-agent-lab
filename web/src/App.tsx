import { useState } from 'react'
import './App.css'
import type { CreatePlanResponse } from './api'
import ItineraryView from './ItineraryView'
import MapPanel from './MapPanel'
import TripForm from './TripForm'

// 阶段 4：表单 + 逐日行程 + 高德地图。历史与保存（阶段 5）在后续实现。
export default function App() {
  const [lastResult, setLastResult] = useState<CreatePlanResponse | null>(null)

  return (
    <div className="layout">
      <aside className="pane pane-history" aria-label="历史记录">
        <h2>历史记录</h2>
        <p className="muted">本次进程中生成过的行程会出现在这里。</p>
      </aside>

      <main className="pane pane-chat" aria-label="对话">
        <h2>Travel Agent Lab</h2>
        <p className="muted">填写需求后生成逐日行程。</p>
        <TripForm onGenerated={setLastResult} />
        {lastResult && (
          <>
            <p className="muted" role="status">plan_id：{lastResult.plan_id}（仅本次进程内有效，尚未保存）</p>
            <ItineraryView itinerary={lastResult.itinerary} />
          </>
        )}
      </main>

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        {lastResult ? (
          <MapPanel key={lastResult.plan_id} days={lastResult.map_days} />
        ) : (
          <p className="muted">生成行程后，这里按日期显示地点与示意线。</p>
        )}
      </section>
    </div>
  )
}
