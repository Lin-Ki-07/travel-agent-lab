import type { Itinerary } from './types'

export interface ActivityTarget {
  dayNumber: number
  activityIndex: number
  placeId: string
  placeName: string
}

const placeSuffixes = ['风景区', '博物馆', '植物园', '动物园', '游乐园', '古城', '公园', '景区']
const editIntent = /(不想去|不想逛|不喜欢|不要去|不去了|不去|换掉|替换)/

function longestMentionedFragment(name: string, text: string): number {
  for (let length = name.length - 1; length >= 2; length -= 1) {
    for (let start = 0; start <= name.length - length; start += 1) {
      if (text.includes(name.slice(start, start + length))) return length
    }
  }
  return 0
}

// 只匹配明确表达“不想去/换掉”的地点名；不从普通聊天中猜测编辑意图。
export function findReplacementTargets(text: string, itinerary: Itinerary): ActivityTarget[] | null {
  const intent = editIntent.exec(text)
  if (!intent) return null
  const mentionedText = text.slice(intent.index + intent[0].length).split(/[，。！？；,!?;\n]/, 1)[0]

  const usedIds = new Set(itinerary.daily_plans.flatMap((day) => day.activities.map((activity) => activity.place_id)))
  const places = itinerary.places.filter((place) => usedIds.has(place.place_id) && place.name)
  const fullMatches = places.filter((place) => mentionedText.includes(place.name))
  const longestFullName = Math.max(0, ...fullMatches.map((place) => place.name.length))
  const matchedPlaces = fullMatches.length
    ? fullMatches.filter((place) => place.name.length === longestFullName)
    : places.filter((place) => placeSuffixes.some((suffix) => {
      if (!place.name.endsWith(suffix)) return false
      const shortName = place.name.slice(0, -suffix.length)
      return shortName.length >= 2 && mentionedText.includes(shortName)
    }))

  const namesById = new Map(matchedPlaces.map((place) => [place.place_id, place.name]))
  if (!namesById.size) {
    const fragmentLengths = places.map((place) => longestMentionedFragment(place.name, mentionedText))
    const longestFragment = Math.max(0, ...fragmentLengths)
    if (longestFragment >= 2) {
      places.forEach((place, index) => {
        if (fragmentLengths[index] === longestFragment) namesById.set(place.place_id, place.name)
      })
    }
  }
  return itinerary.daily_plans.flatMap((day) => day.activities.flatMap((activity, index) =>
    namesById.has(activity.place_id)
      ? [{ dayNumber: day.day_number, activityIndex: index, placeId: activity.place_id, placeName: namesById.get(activity.place_id)! }]
      : [],
  ))
}
