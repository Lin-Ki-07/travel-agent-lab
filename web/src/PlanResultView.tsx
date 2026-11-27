import type { CreatePlanResponse } from './api'

interface Props {
  plan: CreatePlanResponse
  onOpen: () => void
  active: boolean
}

export default function PlanResultView({ plan, onOpen, active }: Props) {
  const request = plan.itinerary.request
  return (
    <button type="button" className="plan-result-card" onClick={onOpen}
      aria-controls="plan-details" aria-expanded={active}>
      <span>
        <strong>{request.destination}旅游攻略</strong>
        <span className="plan-result-subtitle">
          {request.start_date} 起 · {request.days} 天 · {request.travelers} 人
        </span>
      </span>
      <span className="plan-result-arrow" aria-hidden="true">→</span>
    </button>
  )
}
