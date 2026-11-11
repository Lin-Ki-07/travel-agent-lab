// 与后端契约对接：规划、保存、按 plan_id 读取，以及统一的错误解析。
import type { Itinerary, MapDay } from './types'

export interface CreatePlanResponse {
  plan_id: string
  itinerary: Itinerary
  map_days: MapDay[]
}

export interface SavePlanResponse {
  plan_id: string
  saved: boolean
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
  502: '地点、天气或模型服务暂时失败，请稍后重试。',
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
