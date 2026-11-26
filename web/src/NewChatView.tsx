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
  onGenerationChange: (state: 'loading' | 'error', error?: string) => void
  onGenerated: (result: CreatePlanResponse) => void
}

// “新聊天”内容区：欢迎语和表单入口共用一张卡片。输入框由上层提供。
export default function NewChatView({
  defaultPreferences,
  preferencesLoaded,
  formOpen,
  onFormOpenChange,
  prefill,
  formKey,
  onGenerated,
  onGenerationChange,
}: NewChatViewProps) {
  return (
    <div className="new-chat">
      <div className="welcome-card">
        <div className="welcome-message">
          你好，我是 Travel Agent。你可以在下方开始对话，告诉我目的地、出发日期和天数；也可以填写旅行需求表单。
        </div>
        <button type="button" className="form-card-trigger" onClick={() => onFormOpenChange(true)}>
          <span>旅行需求表单</span>
          <span className="form-card-arrow" aria-hidden="true">→</span>
        </button>
      </div>
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
            onGenerationChange={onGenerationChange}
          />
        </div>
      </div>
    </div>
  )
}
