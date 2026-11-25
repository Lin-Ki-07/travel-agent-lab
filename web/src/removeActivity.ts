import type { EditDayRequest } from './api'
import type { DailyPlan } from './types'

export function prepareActivityRemoval(day: DailyPlan, index: number): EditDayRequest {
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
      const adjacent = day.transport_segments.find((segment) =>
        segment.from_place_id === from && segment.to_place_id === day.activities[index].place_id)
        ?? day.transport_segments.find((segment) =>
          segment.from_place_id === day.activities[index].place_id && segment.to_place_id === to)
      if (!adjacent) throw new Error('原行程缺少相邻交通信息，无法安全连接剩余活动。')
      transport_segments.push({ from_place_id: from, to_place_id: to, mode: adjacent.mode, estimated_minutes: null })
    }
  }
  return { activities, transport_segments }
}
