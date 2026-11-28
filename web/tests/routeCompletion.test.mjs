import assert from 'node:assert/strict'
import { test } from 'node:test'
import { runRouteCompletion } from '../src/routeCompletion.ts'

const coded = { plan_id: 'old-plan', missing_count: 0, itinerary: { places: [] } }
const fresh = { plan_id: 'old-plan', itinerary: { places: [], daily_plans: [] } }

test('补全先保存编码结果，再调用缺失路线补全接口', async () => {
  const events = []
  const result = await runRouteCompletion('old-plan',
    async (id) => { assert.equal(id, 'old-plan'); events.push('codes'); return coded },
    async (id) => { assert.equal(id, 'old-plan'); events.push('complete routes'); return fresh },
    (plan) => events.push(plan))
  assert.equal(result, 'done')
  assert.deepEqual(events, ['codes', coded, 'complete routes', fresh])
})

test('编码未补齐时停止查询路线，仍展示已保存地点结果', async () => {
  const partial = { ...coded, missing_count: 2 }
  const updates = []
  assert.equal(await runRouteCompletion('old-plan', async () => partial,
    async () => { throw Error('不得查询路线') }, (plan) => updates.push(plan)), 'missing')
  assert.deepEqual(updates, [partial])
})

test('编码故障不查路线；路线故障保留第一步已保存结果', async () => {
  for (const failCodes of [true, false]) {
    const updates = []
    let routeCalls = 0
    await assert.rejects(runRouteCompletion('old-plan',
      async () => { if (failCodes) throw Error('codes'); return coded },
      async () => { routeCalls++; throw Error('routes') }, (plan) => updates.push(plan)),
      new RegExp(failCodes ? 'codes' : 'routes'))
    assert.equal(routeCalls, failCodes ? 0 : 1)
    assert.deepEqual(updates, failCodes ? [] : [coded])
  }
})
