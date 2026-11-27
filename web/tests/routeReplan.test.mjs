import assert from 'node:assert/strict'
import { test } from 'node:test'
import { runRouteReplan } from '../src/routeReplan.ts'

const coded = { plan_id: 'p', missing_count: 0 }
const fresh = { plan_id: 'p', itinerary: {} }

test('取消不发请求', async () => {
  const unexpected = () => { throw Error('unexpected') }
  assert.equal(await runRouteReplan('p', () => false, unexpected, unexpected, unexpected), 'cancelled')
})

test('编码保存更新后再重查路线并更新', async () => {
  const events = []
  const result = await runRouteReplan('p', () => true,
    async (id) => { assert.equal(id, 'p'); events.push('codes'); return coded },
    async (id) => { assert.equal(id, 'p'); events.push('routes'); return fresh },
    (plan) => events.push(plan === coded ? 'coded update' : 'route update'))
  assert.equal(result, 'done')
  assert.deepEqual(events, ['codes', 'coded update', 'routes', 'route update'])
})

test('缺编码停止重规划但保留地点更新', async () => {
  let updates = 0
  assert.equal(await runRouteReplan('p', () => true,
    async () => ({ ...coded, missing_count: 1 }),
    async () => { throw Error('unexpected') }, () => updates++), 'missing')
  assert.equal(updates, 1)
})

test('补齐故障停止；重规划故障保留已保存地点更新', async () => {
  for (const failCodes of [true, false]) {
    let updates = 0
    let routeCalls = 0
    await assert.rejects(runRouteReplan('p', () => true,
      async () => { if (failCodes) throw Error('codes'); return coded },
      async () => { routeCalls++; throw Error('routes') }, () => updates++),
      new RegExp(failCodes ? 'codes' : 'routes'))
    assert.equal(updates, failCodes ? 0 : 1)
    assert.equal(routeCalls, failCodes ? 0 : 1)
  }
})
