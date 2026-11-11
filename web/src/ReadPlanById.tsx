import { useState, type FormEvent } from 'react'

interface ReadPlanByIdProps {
  loading: boolean
  onLoad: (planId: string) => void
}

// 按 plan_id 读取已保存行程的表单。折叠由外层卡片负责。
export default function ReadPlanById({ loading, onLoad }: ReadPlanByIdProps) {
  const [planId, setPlanId] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = planId.trim()
    if (!trimmed || loading) return
    onLoad(trimmed)
  }

  return (
    <form className="load-by-id" onSubmit={handleSubmit}>
      <input
        value={planId}
        onChange={(e) => setPlanId(e.target.value)}
        placeholder="粘贴已保存行程的 plan_id"
        aria-label="plan_id"
      />
      <button type="submit" disabled={!planId.trim() || loading}>
        {loading ? '读取中…' : '读取'}
      </button>
      <small className="muted">仅能读取本次后端进程中已保存的行程。</small>
    </form>
  )
}
