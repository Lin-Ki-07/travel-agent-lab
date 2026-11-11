import type { CreatePlanResponse } from './api'
import TripForm from './TripForm'
import type { TripFormValues } from './tripRequest'

interface NewChatViewProps {
  formOpen: boolean
  onFormOpenChange: (open: boolean) => void
  // 解析结果：有值时表单以这些字段初始化；formKey 变化会重新挂载表单。
  prefill: TripFormValues | null
  formKey: number
  onGenerated: (result: CreatePlanResponse) => void
}

// “新聊天”内容区：助手问候与可折叠的需求表单卡片。输入框由上层提供。
export default function NewChatView({
  formOpen,
  onFormOpenChange,
  prefill,
  formKey,
  onGenerated,
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
        <TripForm key={formKey} initialValues={prefill ?? undefined} onGenerated={onGenerated} />
      </details>
    </div>
  )
}
