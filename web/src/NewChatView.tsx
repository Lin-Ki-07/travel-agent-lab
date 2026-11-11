import { useState, type FormEvent } from 'react'
import type { CreatePlanResponse } from './api'
import ReadPlanById from './ReadPlanById'
import TripForm from './TripForm'

interface NewChatViewProps {
  loadingById: boolean
  onGenerated: (result: CreatePlanResponse) => void
  onLoadById: (planId: string) => void
}

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

// “新聊天”对话界面：助手问候、可折叠的需求表单卡片、读取卡片，以及底部输入框。
// 输入框目前只做本地回应：自然语言直接规划尚未接入后端，因此引导用户展开表单。
export default function NewChatView({ loadingById, onGenerated, onLoadById }: NewChatViewProps) {
  const [formOpen, setFormOpen] = useState(false)
  const [readOpen, setReadOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = draft.trim()
    if (!text) return
    setDraft('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', text },
      {
        role: 'assistant',
        text: '直接用文字规划暂未接入后端。我已为你展开“旅行需求”表单，请在表单中填写后生成。',
      },
    ])
    setFormOpen(true)
  }

  return (
    <div className="new-chat">
      <div className="chat-bubble assistant">
        你好，我是 Travel Agent。请告诉我目的地、出发日期和天数，我会生成逐日行程。
      </div>

      <details
        className="chat-card"
        open={formOpen}
        onToggle={(event) => setFormOpen(event.currentTarget.open)}
      >
        <summary>旅行需求表单（点击展开或收起）</summary>
        <TripForm onGenerated={onGenerated} />
      </details>

      {messages.map((message, index) => (
        <div key={index} className={`chat-bubble ${message.role}`}>
          {message.text}
        </div>
      ))}

      <details
        className="chat-card"
        open={readOpen}
        onToggle={(event) => setReadOpen(event.currentTarget.open)}
      >
        <summary>读取已保存的行程（按 plan_id）</summary>
        <ReadPlanById loading={loadingById} onLoad={onLoadById} />
      </details>

      <form className="composer" onSubmit={handleSend}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="输入你的旅行想法…"
          aria-label="消息"
        />
        <button type="submit" disabled={!draft.trim()}>
          发送
        </button>
      </form>
    </div>
  )
}
