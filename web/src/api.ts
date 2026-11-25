// 与后端契约对接：规划、保存、按 plan_id 读取，以及统一的错误解析。
import type { Activity, Itinerary, MapDay, TransportSegment } from './types'


export interface CreatePlanResponse {
  plan_id: string
  itinerary: Itinerary
  map_days: MapDay[]
}

export interface SavePlanResponse {
  plan_id: string
  saved: boolean
}

export interface SavedPlanSummary {
  plan_id: string
  destination: string
  start_date: string
  days: number
  generated_at: string
  saved_at: string
}

export interface SavedPlansResponse {
  plans: SavedPlanSummary[]
}

export interface ParseRequestResponse {
  fields: Record<string, string>
  missing: string[]
  issues: string[]
  summary: string
}

export interface ChatResponse {
  kind: 'answer' | 'clarify' | 'edit_target'
  message: string
  target?: { day_number: number; activity_index: number; place_id: string }
}

export interface EditDraftResponse {
  kind: 'edit_draft'
  message: string
  draft: {
    plan_id: string
    source_fingerprint: string
    day_number: number
    activity_index: number
    original_place_id: string
    candidate_place_id: string
    activities: Activity[]
    transport_segments: TransportSegment[]
  }
}

export function createEditDraft(planId: string, target: { dayNumber: number; activityIndex: number; placeId: string }, candidateId: string): Promise<EditDraftResponse> {
  return requestJson<EditDraftResponse>(`/api/plans/${encodeURIComponent(planId)}/edit-draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      day_number: target.dayNumber,
      activity_index: target.activityIndex,
      original_place_id: target.placeId,
      candidate_place_id: candidateId,
    }),
  })
}

export function confirmEditDraft(planId: string, draft: EditDraftResponse['draft']): Promise<CreatePlanResponse> {
  return requestJson<CreatePlanResponse>(`/api/plans/${encodeURIComponent(planId)}/edit-draft/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
  })
}

export function sendChat(
  text: string,
  planId: string | null,
  history: { role: 'user' | 'assistant'; content: string }[],
  baseUrl = '',
): Promise<ChatResponse> {
  return requestJson<ChatResponse>(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, plan_id: planId, history }),
  })
}

export class PlanApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'PlanApiError'
    this.status = status
  }
}

// 后端错误体为 {"detail": "..."}；若是 FastAPI 的校验数组，取其中的 msg 文本。
export function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  const detail = (body as { detail: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : ''))
      .filter(Boolean)
    return messages.length ? messages.join('；') : null
  }
  return null
}

const FALLBACK_BY_STATUS: Record<number, string> = {
  404: '行程不存在，或尚未保存。',
  422: '输入无效，请检查表单。',
  502: '无法连接后端服务，请确认 uvicorn 已在 127.0.0.1:8000 启动。',
}

async function requestJson<T>(url: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch {
    throw new PlanApiError('无法连接后端服务，请确认 uvicorn 已在 127.0.0.1:8000 启动。', null)
  }

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (response.ok) {
    return payload as T
  }

  const detail = extractDetail(payload)
  const fallback = FALLBACK_BY_STATUS[response.status] ?? `服务返回异常（HTTP ${response.status}）。`
  throw new PlanApiError(detail ?? fallback, response.status)
}

export function createPlan(
  body: Record<string, string>,
  baseUrl = '',
): Promise<CreatePlanResponse> {
  return requestJson<CreatePlanResponse>(`${baseUrl}/api/plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// 把一句自然语言需求解析为表单字段；只解析，不保存，不生成行程。
export function parseRequest(text: string, baseUrl = ''): Promise<ParseRequestResponse> {
  return requestJson<ParseRequestResponse>(`${baseUrl}/api/plans/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

// 只发送 plan_id，不回传行程内容；后端只会把当前进程中已生成的行程标记为已保存。
export function savePlan(planId: string, baseUrl = ''): Promise<SavePlanResponse> {
  return requestJson<SavePlanResponse>(
    `${baseUrl}/api/plans/${encodeURIComponent(planId)}/save`,
    { method: 'POST' },
  )
}

// 仅能读取已保存的行程；未知或未保存的 ID 返回 404。
export function getPlan(planId: string, baseUrl = ''): Promise<CreatePlanResponse> {
  return requestJson<CreatePlanResponse>(
    `${baseUrl}/api/plans/${encodeURIComponent(planId)}`,
    { method: 'GET' },
  )
}

export function deletePlan(planId: string, baseUrl = ''): Promise<{ plan_id: string; deleted: boolean }> {
  return requestJson<{ plan_id: string; deleted: boolean }>(`${baseUrl}/api/plans/${encodeURIComponent(planId)}`, { method: 'DELETE' })
    .catch((error: unknown) => {
      if (error instanceof PlanApiError && error.status === 405) {
        throw new PlanApiError('当前后端尚未加载删除接口。请重启 uvicorn 后重试。', 405)
      }
      throw error
    })
}

export function listSavedPlans(baseUrl = ''): Promise<SavedPlansResponse> {
  return requestJson<SavedPlansResponse>(`${baseUrl}/api/plans`, {
    method: 'GET',
  })
}

export interface EditDayRequest {
  activities: Activity[]
  transport_segments: TransportSegment[]
}

export function updatePlanDay(
  planId: string,
  dayNumber: number,
  body: EditDayRequest,
  baseUrl = '',
): Promise<CreatePlanResponse> {
  return requestJson<CreatePlanResponse>(
    `${baseUrl}/api/plans/${encodeURIComponent(planId)}/days/${dayNumber}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
}

export interface PreferencesResponse {
  preferences: string[]
}

export function getPreferences(baseUrl = ''): Promise<PreferencesResponse> {
  return requestJson<PreferencesResponse>(`${baseUrl}/api/preferences`, { method: 'GET' })
}

export function putPreferences(
  preferences: string[],
  baseUrl = '',
): Promise<PreferencesResponse> {
  return requestJson<PreferencesResponse>(`${baseUrl}/api/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preferences }),
  })
}
