// 与后端契约对接。规划请求与错误解析；map_days 在阶段 4 使用。
import type { Itinerary } from './types'

export interface CreatePlanResponse {
  plan_id: string
  itinerary: Itinerary
  map_days: unknown[]
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

export async function createPlan(
  body: Record<string, string>,
  baseUrl = '',
): Promise<CreatePlanResponse> {
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/plans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
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
    return payload as CreatePlanResponse
  }

  const detail = extractDetail(payload)
  if (response.status === 422) {
    throw new PlanApiError(detail ?? '输入无效，请检查表单。', 422)
  }
  if (response.status === 502) {
    throw new PlanApiError(detail ?? '地点、天气或模型服务暂时失败，请稍后重试。', 502)
  }
  throw new PlanApiError(detail ?? `服务返回异常（HTTP ${response.status}）。`, response.status)
}
