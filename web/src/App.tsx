import { useState } from 'react'
import './App.css'
import type { CreatePlanResponse } from './api'
import TripForm from './TripForm'

// 阶段 2：表单与生成状态。行程展示（阶段 3）、地图（阶段 4）、历史与保存（阶段 5）在后续实现。
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
          <div className="card" role="status">
            <h3>行程已生成</h3>
            <p className="muted">plan_id：{lastResult.plan_id}</p>
            <p className="muted">逐日展示将在阶段 3 实现。</p>
          </div>
        )}
      </main>

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        <p className="muted">生成行程后，这里按日期显示地点与示意线。</p>
      </section>
    </div>
  )
}
