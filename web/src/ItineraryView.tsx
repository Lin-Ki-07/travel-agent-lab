import type { Itinerary } from './types'
import {
  budgetStatus,
  describeDay,
  formatCost,
  formatSegmentDuration,
  formatTimeRange,
  formatWeather,
  placeNameById,
} from './itineraryFormat'

interface ItineraryViewProps {
  itinerary: Itinerary
}

export default function ItineraryView({ itinerary }: ItineraryViewProps) {
  const { places, daily_plans: days } = itinerary

  return (
    <div className="itinerary">
      <div className="card">
        <h3>行程总览</h3>
        <p className="muted">
          {itinerary.request.destination} · {itinerary.request.start_date} 起 {itinerary.request.days} 天 ·{' '}
          {itinerary.request.travelers} 人
        </p>
        <p>{budgetStatus(itinerary)}</p>
        <p className="muted">生成时间：{itinerary.generated_at}</p>
      </div>

      {days.map((day) => (
        <section className="card day-card" key={day.day_number}>
          <h3>{describeDay(day)}</h3>
          <p className="muted">天气：{formatWeather(day.weather)}</p>

          <ol className="activity-list">
            {day.activities.map((activity, index) => (
              <li key={`${activity.place_id}-${index}`}>
                <div className="activity-time">{formatTimeRange(activity)}</div>
                <div>
                  <strong>{placeNameById(places, activity.place_id)}</strong>
                  <div>{activity.description}</div>
                </div>
              </li>
            ))}
          </ol>

          {day.transport_segments.length > 0 && (
            <div className="transport">
              <h4>交通段</h4>
              <ul>
                {day.transport_segments.map((segment, index) => (
                  <li key={index}>
                    {placeNameById(places, segment.from_place_id)} → {placeNameById(places, segment.to_place_id)}
                    ：{segment.mode}，{formatSegmentDuration(segment)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="muted">
            当日费用：{formatCost(day.estimated_cost_cny)}
            {day.cost_basis ? `（${day.cost_basis}）` : ''}
          </p>
        </section>
      ))}
    </div>
  )
}
