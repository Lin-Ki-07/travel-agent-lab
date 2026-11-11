import type { CreatePlanResponse } from './api'
import ReadPlanById from './ReadPlanById'
import TripForm from './TripForm'

interface NewChatViewProps {
  formOpen: boolean
  onFormOpenChange: (open: boolean) => void
  loadingById: boolean
  onGenerated: (result: CreatePlanResponse) => void
  onLoadById: (planId: string) => void
}

// “新聊天”内容区：助手问候、可折叠的需求表单卡片、读取卡片。输入框由上层提供。
export default function NewChatView({
  formOpen,
  onFormOpenChange,
  loadingById,
  onGenerated,
  onLoadById,
}: NewChatViewProps) {
  return (
    <div className="new-chat">
      <div className="chat-bubble assistant">
        你好，我是 Travel Agent。请告诉我目的地、出发日期和天数，我会生成逐日行程。
      </div>

      <details
        className="chat-card"
        open={formOpen}
        onToggle={(event) => onFormOpenChange(event.currentTarget.open)}
      >
        <summary>旅行需求表单（点击展开或收起）</summary>
        <TripForm onGenerated={onGenerated} />
      </details>

      <details className="chat-card">
        <summary>读取已保存的行程（按 plan_id）</summary>
        <ReadPlanById loading={loadingById} onLoad={onLoadById} />
      </details>
    </div>
  )
}
