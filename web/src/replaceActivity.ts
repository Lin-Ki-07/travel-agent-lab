import type { EditDayRequest } from './api'
import type { ActivityTarget } from './editIntent'
import type { DailyPlan } from './types'

export function prepareActivityReplacement(
  day: DailyPlan,
  target: ActivityTarget,
  candidateId: string,
  description: string,
  incomingMode: string,
  outgoingMode: string,
): EditDayRequest {
  if (day.day_number !== target.dayNumber || day.activities[target.activityIndex]?.place_id !== target.placeId) {
    throw new Error('行程已变化，请重新选择要替换的活动。')
  }
  if (!candidateId || candidateId === target.placeId) throw new Error('请选择其他候选地点。')
  const nextDescription = description.trim()
  if (!nextDescription) throw new Error('请填写新活动内容。')

  const activities = day.activities.map((activity, index) => index === target.activityIndex
    ? { ...activity, place_id: candidateId, description: nextDescription }
    : activity)
  const transport_segments: EditDayRequest['transport_segments'] = []
  for (let i = 1; i < activities.length; i += 1) {
    const from = activities[i - 1].place_id
    const to = activities[i].place_id
    if (from === to) continue
    if (i - 1 === target.activityIndex || i === target.activityIndex) {
      const mode = (i === target.activityIndex ? incomingMode : outgoingMode).trim()
      if (!mode) throw new Error(`请填写第 ${i} 段交通方式。`)
      transport_segments.push({ from_place_id: from, to_place_id: to, mode, estimated_minutes: null })
    } else {
      const existing = day.transport_segments.find((segment) =>
        segment.from_place_id === from && segment.to_place_id === to)
      if (!existing) throw new Error('原交通段已变化，请重新选择。')
      transport_segments.push(existing)
    }
  }
  return { activities, transport_segments }
}
