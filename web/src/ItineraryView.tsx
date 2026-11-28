import { useState } from 'react'
import { clampDayIndex } from './mapModel'
import DayEditor from './DayEditor'
import type { EditDayRequest } from './api'
import type { Itinerary } from './types'
import {
  describeDay,
  formatCost,
  formatTransportMode,
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
  selectedDayIndex?: number
  onDayIndexChange?: (index: number) => void
  replanningRoutes?: boolean
  onReplanRoutes?: () => void
  completingRoutes?: boolean
  onCompleteRoutes?: () => void
  onEditDay: (dayNumber: number, body: EditDayRequest) => Promise<void>
}

export default function ItineraryView({
  itinerary, editable, savingEdit, onEditDay, completingRoutes = false, onCompleteRoutes, replanningRoutes = false, onReplanRoutes, selectedDayIndex, onDayIndexChange,
}: ItineraryViewProps) {
  const [editingDay, setEditingDay] = useState<number | null>(null)
  const [dayIndex, setDayIndex] = useState(0)
  const { places, daily_plans: days } = itinerary
  const safeIndex = clampDayIndex(selectedDayIndex ?? dayIndex, days.length)
  const selectedDay = days[safeIndex]

  return (
    <div className="itinerary">
      <div className="day-tabs" role="tablist" aria-label="按日查看行程">
        {days.map((day, index) => (
          <button
            key={day.day_number}
            type="button"
            role="tab"
            aria-selected={index === safeIndex}
            className={index === safeIndex ? 'day-tab active' : 'day-tab'}
            onClick={() => { setDayIndex(index); onDayIndexChange?.(index) }}
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
              {editable && onCompleteRoutes && <button type="button"
                disabled={savingEdit || completingRoutes || replanningRoutes || editingDay !== null}
                onClick={onCompleteRoutes}>{completingRoutes ? '补全中…' : '补全交通'}</button>}
              {editable && onReplanRoutes && <button type="button"
                disabled={savingEdit || completingRoutes || replanningRoutes || editingDay !== null}
                onClick={onReplanRoutes}>{replanningRoutes ? '处理中…' : '重新规划交通'}</button>}
              <ul>
                {selectedDay.transport_segments.map((segment, index) => (
                  <li key={index}>
                    {placeNameById(places, segment.from_place_id)} → {placeNameById(places, segment.to_place_id)}
                    ：{formatTransportMode(segment.mode)}，{formatSegmentDuration(segment)}
                    {formatRouteDetails(segment) && <div className="muted">{formatRouteDetails(segment)}</div>}
                  </li>
                ))}
              </ul>
              <p className="muted">路线为查询快照。</p>
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
