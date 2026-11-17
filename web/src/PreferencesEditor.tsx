import { useState, type FormEvent } from 'react'
import { putPreferences, PlanApiError } from './api'

interface Props {
  preferences: string[]
  onSaved: (preferences: string[]) => void
}

export default function PreferencesEditor({ preferences, onSaved }: Props) {
  const [text, setText] = useState(preferences.join(','))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return
    setError('')
    setNotice('')
    const items = text.trim() ? text.split(',').map((item) => item.trim()) : []
    try {
      setLoading(true)
      const result = await putPreferences(items)
      onSaved(result.preferences)
      setNotice(result.preferences.length ? '默认偏好已保存。' : '默认偏好已清除。')
    } catch (caught) {
      setError(caught instanceof PlanApiError ? caught.message : '保存默认偏好失败。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="preferences-editor" onSubmit={save}>
      <label htmlFor="default-preferences">默认旅行偏好</label>
      <input
        id="default-preferences"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="例如：美食,博物馆"
        disabled={loading}
      />
      <p className="muted">用英文逗号分隔；清空并保存可删除默认偏好。</p>
      <div className="preferences-actions">
        <button type="submit" disabled={loading}>保存默认偏好</button>
      </div>
      {error && <p role="alert" className="field-error">{error}</p>}
      {notice && <p role="status" className="muted">{notice}</p>}
    </form>
  )
}
