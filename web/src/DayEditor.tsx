import { useState, type FormEvent } from 'react'
import type { EditDayRequest } from './api'
import type { Activity, DailyPlan, Place } from './types'

interface Props {
  day: DailyPlan
  places: Place[]
  disabled: boolean
  onCancel: () => void
  onSubmit: (dayNumber: number, body: EditDayRequest) => Promise<void>
}

export default function DayEditor({ day, places, disabled, onCancel, onSubmit }: Props) {
  const [activities, setActivities] = useState<Activity[]>(
    day.activities.map((activity) => ({ ...activity })),
  )
  const [modes, setModes] = useState<string[]>(() => {
    let segmentIndex = 0
    return day.activities.slice(1).map((activity, index) => {
      if (day.activities[index].place_id === activity.place_id) return ''
      return day.transport_segments[segmentIndex++]?.mode ?? ''
    })
  })
  const [error, setError] = useState('')

  function changeActivity(index: number, changes: Partial<Activity>) {
    setActivities((current) =>
      current.map((activity, i) => i === index ? { ...activity, ...changes } : activity),
    )
  }

  function removeActivity(index: number) {
    setActivities((current) => current.filter((_, i) => i !== index))
    setModes([])
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    const transport_segments: EditDayRequest['transport_segments'] = []
    for (let i = 1; i < activities.length; i += 1) {
      const previous = activities[i - 1]
      const current = activities[i]
      if (previous.place_id === current.place_id) continue

      const mode = (modes[i - 1] ?? '').trim()
      if (!mode) {
        setError(`第 ${i} 段交通方式不能为空`)
        return
      }
      transport_segments.push({
        from_place_id: previous.place_id,
        to_place_id: current.place_id,
        mode,
        estimated_minutes: null,
      })
    }

    try {
      await onSubmit(day.day_number, { activities, transport_segments })
    } catch {
      // App 显示后端错误；保留当前编辑内容供用户修正。
    }
  }

  return (
    <form className="day-editor" onSubmit={submit}>
      <h4>编辑第 {day.day_number} 天</h4>
      <p className="muted">地点仅可从本行程已查询地点中选择。修改后当天及总费用变为未知。</p>

      {activities.map((activity, index) => (
        <div className="day-editor-row" key={index}>
          <label>
            地点
            <select
              value={activity.place_id}
              onChange={(event) => changeActivity(index, { place_id: event.target.value })}
              disabled={disabled}
            >
              {places.map((place) => (
                <option key={place.place_id} value={place.place_id}>{place.name}</option>
              ))}
            </select>
          </label>
          <label>
            开始
            <input
              type="time"
              value={activity.start_time.slice(0, 5)}
              onChange={(event) => changeActivity(index, { start_time: event.target.value })}
              disabled={disabled}
              required
            />
          </label>
          <label>
            结束
            <input
              type="time"
              value={activity.end_time.slice(0, 5)}
              onChange={(event) => changeActivity(index, { end_time: event.target.value })}
              disabled={disabled}
              required
            />
          </label>
          <label>
            活动内容
            <input
              value={activity.description}
              onChange={(event) => changeActivity(index, { description: event.target.value })}
              disabled={disabled}
              required
            />
          </label>
          <button
            type="button"
            onClick={() => removeActivity(index)}
            disabled={disabled || activities.length === 1}
          >
            删除活动
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={() => setActivities((current) => [
          ...current,
          {
            place_id: places[0].place_id,
            description: '',
            start_time: '09:00',
            end_time: '10:00',
          },
        ])}
        disabled={disabled || places.length === 0}
      >
        添加活动
      </button>

      {activities.slice(1).map((activity, index) => (
        activities[index].place_id !== activity.place_id && (
          <label key={index}>
            第 {index + 1} 段交通方式
            <input
              value={modes[index] ?? ''}
              onChange={(event) => setModes((current) => {
                const next = [...current]
                next[index] = event.target.value
                return next
              })}
              disabled={disabled}
              placeholder="例如：步行；请自行核实可行性"
              required
            />
          </label>
        )
      ))}

      {error && <p role="alert" className="field-error">{error}</p>}
      <div className="day-editor-actions">
        <button type="button" onClick={onCancel} disabled={disabled}>取消</button>
        <button type="submit" disabled={disabled}>
          {disabled ? '保存中…' : '保存当天修改'}
        </button>
      </div>
    </form>
  )
}
