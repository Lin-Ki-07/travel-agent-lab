import type { Itinerary } from './types'

export interface ActivityTarget {
  dayNumber: number
  activityIndex: number
  placeId: string
  placeName: string
}

// 只匹配明确表达“不想去/换掉”的地点名；不从普通聊天中猜测编辑意图。
export function findReplacementTargets(text: string, itinerary: Itinerary): ActivityTarget[] | null {
  if (!/(不想去|不喜欢|换掉|替换|不要去)/.test(text)) return null

  const names = [...itinerary.places]
    .filter((place) => place.name && text.includes(place.name))
    .sort((a, b) => b.name.length - a.name.length)
  if (!names.length) return []

  const longestName = names[0].name
  const namedPlaces = names.filter((place) => place.name === longestName)
  const ids = new Set(namedPlaces.map((place) => place.place_id))
  return itinerary.daily_plans.flatMap((day) => day.activities.flatMap((activity, index) =>
    ids.has(activity.place_id)
      ? [{ dayNumber: day.day_number, activityIndex: index, placeId: activity.place_id, placeName: longestName }]
      : [],
  ))
}
