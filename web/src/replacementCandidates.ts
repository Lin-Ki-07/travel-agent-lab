import type { ActivityTarget } from './editIntent'
import type { Itinerary, Place } from './types'

export function replacementCandidates(itinerary: Itinerary, target: ActivityTarget): Place[] {
  const day = itinerary.daily_plans.find((item) => item.day_number === target.dayNumber)
  if (!day || day.activities[target.activityIndex]?.place_id !== target.placeId) return []
  const dayIds = new Set(day.activities.map((activity) => activity.place_id))
  return itinerary.places.filter((place) =>
    !dayIds.has(place.place_id) && Number.isFinite(place.latitude) && Number.isFinite(place.longitude))
}
