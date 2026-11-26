import { useState } from 'react'
import DayEditor from './DayEditor'
import type { EditDayRequest } from './api'
import type { Itinerary } from './types'
import {
  describeDay,
  formatCost,
  formatSegmentDuration,
  formatRouteDetails,
  formatTimeRange,
  formatWeather,
  placeNameById,
} from './itineraryFormat'

interface ItineraryViewProps {
  itinerary: Itinerary
  editable: boolean
  savingEdit: boolean
  onEditDay: (dayNumber: number, body: EditDayRequest) => Promise<void>
}

export default function ItineraryView({
  itinerary, editable, savingEdit, onEditDay,
}: ItineraryViewProps) {
  const [editingDay, setEditingDay] = useState<number | null>(null)
  const [dayIndex, setDayIndex] = useState(0)
  const { places, daily_plans: days } = itinerary
  const selectedDay = days[Math.min(dayIndex, days.length - 1)]

  return (
    <div className="itinerary">
      <div className="day-tabs" role="tablist" aria-label="按日查看行程">
        {days.map((day, index) => (
          <button
            key={day.day_number}
            type="button"
            role="tab"
            aria-selected={index === dayIndex}
            className={index === dayIndex ? 'day-tab active' : 'day-tab'}
            onClick={() => setDayIndex(index)}
          >
            第 {day.day_number} 天
          </button>
        ))}
      </div>

      {selectedDay && (
        <section className="card day-card" key={selectedDay.day_number}>
          <h3>{describeDay(selectedDay)}</h3>
          <p className="muted">
            天气快照：{formatWeather(selectedDay.weather)}
            （来源：{selectedDay.weather.source}；查询时间：{selectedDay.weather.queried_at}）
          </p>
          {editable && (
            <button
              type="button"
              onClick={() => setEditingDay(selectedDay.day_number)}
              disabled={savingEdit}
            >
              编辑当天
            </button>
          )}
          {editingDay === selectedDay.day_number && (
            <DayEditor
              day={selectedDay}
              places={places}
              disabled={savingEdit}
              onCancel={() => setEditingDay(null)}
              onSubmit={async (dayNumber, body) => {
                await onEditDay(dayNumber, body)
                setEditingDay(null)
              }}
            />
          )}
          <ol className="activity-list">
            {selectedDay.activities.map((activity, index) => (
              <li key={`${activity.place_id}-${index}`}>
                <div className="activity-time">{formatTimeRange(activity)}</div>
                <div>
                  <strong>{placeNameById(places, activity.place_id)}</strong>
                  <div>{activity.description}</div>
                </div>
              </li>
            ))}
          </ol>

          {selectedDay.transport_segments.length > 0 && (
            <div className="transport">
              <h4>交通段</h4>
              <ul>
                {selectedDay.transport_segments.map((segment, index) => (
                  <li key={index}>
                    {placeNameById(places, segment.from_place_id)} → {placeNameById(places, segment.to_place_id)}
                    ：{segment.mode}，{formatSegmentDuration(segment)}
                    <div className="muted">{formatRouteDetails(segment)}</div>
                  </li>
                ))}
              </ul>
              <p className="muted">路线为查询快照；地图当前仍显示地点顺序示意线。</p>
            </div>
          )}

          <p className="muted">
            当日费用估算快照：{formatCost(selectedDay.estimated_cost_cny)}
            {selectedDay.cost_basis ? `（${selectedDay.cost_basis}）` : ''}
          </p>
        </section>
      )}
    </div>
  )
}
