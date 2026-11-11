import './App.css'

// 阶段 1：三栏骨架。表单、行程、地图和历史记录在后续阶段实现。
export default function App() {
  return (
    <div className="layout">
      <aside className="pane pane-history" aria-label="历史记录">
        <h2>历史记录</h2>
        <p className="muted">本次进程中生成过的行程会出现在这里。</p>
      </aside>

      <main className="pane pane-chat" aria-label="对话">
        <h2>Travel Agent Lab</h2>
        <p className="muted">请在下方填写需求，生成逐日行程。</p>
      </main>

      <section className="pane pane-map" aria-label="地图">
        <h2>地图</h2>
        <p className="muted">生成行程后，这里按日期显示地点与示意线。</p>
      </section>
    </div>
  )
}
