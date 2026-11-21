import type { EditDayRequest } from './api'
import type { DailyPlan } from './types'

export function prepareActivityRemoval(day: DailyPlan, index: number, bridgeMode: string): EditDayRequest {
  if (index < 0 || index >= day.activities.length) throw new Error('活动已变化，请重新选择。')
  if (day.activities.length === 1) throw new Error('当天至少需要保留一项活动。')

  const activities = day.activities.filter((_, activityIndex) => activityIndex !== index)
  const transport_segments: EditDayRequest['transport_segments'] = []
  for (let i = 1; i < activities.length; i += 1) {
    const from = activities[i - 1].place_id
    const to = activities[i].place_id
    if (from === to) continue

    const existing = day.transport_segments.find((segment) =>
      segment.from_place_id === from && segment.to_place_id === to)
    if (existing) {
      transport_segments.push(existing)
    } else {
      const mode = bridgeMode.trim()
      if (!mode) throw new Error('请填写删掉该活动后新连接的交通方式。')
      transport_segments.push({ from_place_id: from, to_place_id: to, mode, estimated_minutes: null })
    }
  }
  return { activities, transport_segments }
}

export function needsBridgeMode(day: DailyPlan, index: number): boolean {
  if (index <= 0 || index >= day.activities.length - 1) return false
  const from = day.activities[index - 1].place_id
  const to = day.activities[index + 1].place_id
  return from !== to && !day.transport_segments.some((segment) =>
    segment.from_place_id === from && segment.to_place_id === to)
}
