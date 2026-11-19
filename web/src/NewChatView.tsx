import type { CreatePlanResponse } from './api'
import TripForm from './TripForm'
import type { TripFormValues } from './tripRequest'

interface NewChatViewProps {
  defaultPreferences: string[]
  preferencesLoaded: boolean
  formOpen: boolean
  onFormOpenChange: (open: boolean) => void
  // 解析结果：有值时表单以这些字段初始化；formKey 变化会重新挂载表单。
  prefill: TripFormValues | null
  formKey: number
  onGenerated: (result: CreatePlanResponse) => void
}

// “新聊天”内容区：卡片打开浮层表单。输入框由上层提供。
export default function NewChatView({
  defaultPreferences,
  preferencesLoaded,
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

      <button type="button" className="chat-card form-card-trigger" onClick={() => onFormOpenChange(true)}>
        旅行需求表单
      </button>
      <div className={formOpen ? 'form-overlay' : 'form-overlay form-overlay-hidden'}>
        <button
          type="button"
          className="form-overlay-backdrop"
          aria-label="关闭旅行需求表单"
          tabIndex={formOpen ? 0 : -1}
          onClick={() => onFormOpenChange(false)}
        />
        <div
          className="form-dialog"
          role="dialog"
          aria-modal="true"
          aria-label="旅行需求表单"
          onKeyDown={(event) => {
            if (event.key === 'Escape') onFormOpenChange(false)
          }}
        >
          <button type="button" className="form-close" onClick={() => onFormOpenChange(false)}>
            关闭
          </button>
          <TripForm
            key={formKey}
            initialValues={prefill ?? undefined}
            defaultPreferences={defaultPreferences}
            preferencesLoaded={preferencesLoaded}
            onGenerated={onGenerated}
          />
        </div>
      </div>
    </div>
  )
}
