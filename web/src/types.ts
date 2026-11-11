// 与 API_CONTRACT.md 及 core/trip_models.py 对齐的响应类型。
// 时间字段由后端 jsonable_encoder 输出为 "HH:MM:SS"；日期为 "YYYY-MM-DD"。

export interface Place {
  place_id: string
  name: string
  address: string
  latitude: number
  longitude: number
  source: string
  queried_at: string
}

export interface WeatherSnapshot {
  forecast_date: string
  condition: string | null
  min_temp_c: number | null
  max_temp_c: number | null
  available: boolean
  source: string
  queried_at: string
}

export interface Activity {
  place_id: string
  description: string
  start_time: string
  end_time: string
}

export interface TransportSegment {
  from_place_id: string
  to_place_id: string
  mode: string
  estimated_minutes: number | null
}

export interface DailyPlan {
  day_number: number
  plan_date: string
  weather: WeatherSnapshot
  activities: Activity[]
  transport_segments: TransportSegment[]
  estimated_cost_cny: number | null
  cost_basis: string | null
}

export interface TripRequestData {
  destination: string
  start_date: string
  days: number
  travelers: number
  budget_cny: number | null
  preferences: string[]
}

export interface Itinerary {
  request: TripRequestData
  places: Place[]
  daily_plans: DailyPlan[]
  estimated_total_cny: number | null
  generated_at: string
}
