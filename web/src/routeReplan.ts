import type { CompleteCitycodesResponse, CreatePlanResponse } from './api'

// Two independent saves: expose the citycode result before requesting new routes.
export async function runRouteReplan(
  planId: string,
  confirm: () => boolean,
  complete: (id: string) => Promise<CompleteCitycodesResponse>,
  replan: (id: string) => Promise<CreatePlanResponse>,
  update: (plan: CreatePlanResponse) => void,
): Promise<'cancelled' | 'missing' | 'done'> {
  if (!confirm()) return 'cancelled'
  const coded = await complete(planId)
  update(coded)
  if (coded.missing_count > 0) return 'missing'
  const result = await replan(planId)
  update(result)
  return 'done'
}
