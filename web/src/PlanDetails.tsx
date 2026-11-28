import type { CreatePlanResponse, EditDayRequest } from './api'
import ItineraryView from './ItineraryView'
import EvidenceView from './EvidenceView'

export interface PlanDetailsProps {
  plan: CreatePlanResponse
  notice: { kind: 'success' | 'error'; text: string } | null
  isSaved: boolean
  saving: boolean
  savingEdit: boolean
  selectedDayIndex: number
  onDayIndexChange: (index: number) => void
  completingRoutes: boolean
  onCompleteRoutes: () => void
  replanningRoutes: boolean
  onReplanRoutes: () => void
  onSave: () => void
  onEditDay: (dayNumber: number, body: EditDayRequest) => Promise<void>
}

export default function PlanDetails({ plan, notice, isSaved, saving, savingEdit, onSave, onEditDay, completingRoutes, onCompleteRoutes, replanningRoutes, onReplanRoutes, selectedDayIndex, onDayIndexChange }: PlanDetailsProps) {
  return (
    <div className="plan-details">
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
              selectedDayIndex={selectedDayIndex}
              onDayIndexChange={onDayIndexChange}
              editable={isSaved}
              savingEdit={savingEdit}
              onEditDay={onEditDay}
              completingRoutes={completingRoutes}
              onCompleteRoutes={onCompleteRoutes}
              replanningRoutes={replanningRoutes}
              onReplanRoutes={onReplanRoutes}
            />
            <EvidenceView evidence={plan.itinerary.web_evidence ?? ''} />
    </div>
  )
}
