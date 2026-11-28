import type { CompleteCitycodesResponse, CreatePlanResponse } from './api'

// Each endpoint saves independently; keep the citycode result if routing fails.
export async function runRouteCompletion(
  planId: string,
  completeCitycodes: (id: string) => Promise<CompleteCitycodesResponse>,
  completeRoutes: (id: string) => Promise<CreatePlanResponse>,
  update: (plan: CreatePlanResponse) => void,
): Promise<'missing' | 'done'> {
  const coded = await completeCitycodes(planId)
  update(coded)
  if (coded.missing_count > 0) return 'missing'
  const result = await completeRoutes(planId)
  update(result)
  return 'done'
}
