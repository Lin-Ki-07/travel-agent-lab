import { useState } from 'react'
import type { CreatePlanResponse, EditDayRequest } from './api'
import ItineraryView from './ItineraryView'
import EvidenceView from './EvidenceView'

interface Props {
  plan: CreatePlanResponse
  notice: { kind: 'success' | 'error'; text: string } | null
  isSaved: boolean
  saving: boolean
  savingEdit: boolean
  onSave: () => void
  onEditDay: (dayNumber: number, body: EditDayRequest) => Promise<void>
}

export default function PlanResultView({
  plan, notice, isSaved, saving, savingEdit, onSave, onEditDay,
}: Props) {
  const [open, setOpen] = useState(false)
  const request = plan.itinerary.request

  return (
    <>
      <button type="button" className="plan-result-card" onClick={() => setOpen(true)}>
        <span>
          <strong>{request.destination}旅游攻略</strong>
          <span className="plan-result-subtitle">
            {request.start_date} 起 · {request.days} 天 · {request.travelers} 人
          </span>
        </span>
        <span className="plan-result-arrow" aria-hidden="true">→</span>
      </button>
      {open && (
        <div className="form-overlay">
          <button
            type="button"
            className="form-overlay-backdrop"
            aria-label="关闭行程详情"
            onClick={() => setOpen(false)}
          />
          <div
            className="form-dialog plan-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={`${request.destination}行程详情`}
            onKeyDown={(event) => {
              if (event.key === 'Escape') setOpen(false)
            }}
          >
            <button type="button" className="form-close" onClick={() => setOpen(false)}>
              关闭
            </button>
            {notice && (
              <div
                className={notice.kind === 'error' ? 'banner banner-error' : 'banner banner-success'}
                role={notice.kind === 'error' ? 'alert' : 'status'}
              >
                {notice.text}
              </div>
            )}
            <div className="plan-toolbar">
              <p className="muted">
                {isSaved ? '已保存' : '未保存，刷新页面后无法重新打开'}
              </p>
              <button type="button" onClick={onSave} disabled={saving || isSaved}>
                {isSaved ? '已保存' : saving ? '保存中…' : '保存当前行程'}
              </button>
            </div>
            <ItineraryView
              itinerary={plan.itinerary}
              editable={isSaved}
              savingEdit={savingEdit}
              onEditDay={onEditDay}
            />
            <EvidenceView evidence={plan.itinerary.web_evidence ?? ''} />
          </div>
        </div>
      )}
    </>
  )
}
