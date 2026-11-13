import type { FormEvent } from 'react'

interface ChatComposerProps {
  draft: string
  onDraftChange: (value: string) => void
  onSend: (text: string) => void
  placeholder?: string
  disabled?: boolean
}

// 固定在中间栏底部的输入框：圆角容器，右侧圆形发送按钮。
export default function ChatComposer({
  draft,
  onDraftChange,
  onSend,
  placeholder,
  disabled = false,
}: ChatComposerProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || disabled) return
    onSend(text)
  }

  return (
    <form className="composer-box" onSubmit={handleSubmit}>
      <input
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder={placeholder ?? '和旅行助手说说你的想法…'}
        aria-label="消息"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !draft.trim()} aria-label="发送">
        ↑
      </button>
    </form>
  )
}
