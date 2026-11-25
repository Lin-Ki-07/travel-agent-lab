import assert from 'node:assert/strict'
import { test } from 'node:test'

import { prepareActivityRemoval } from '../src/removeActivity.ts'

const activity = (place_id) => ({ place_id, description: place_id, start_time: '09:00', end_time: '10:00' })
const segment = (from_place_id, to_place_id, mode, estimated_minutes = 15) => ({
  from_place_id, to_place_id, mode, estimated_minutes,
})

const day = {
  activities: [activity('P1'), activity('P2'), activity('P3')],
  transport_segments: [segment('P1', 'P2', '步行'), segment('P2', 'P3', '公交')],
}

test('删除首项和末项保留剩余连接', () => {
  const first = prepareActivityRemoval(day, 0)
  assert.deepEqual(first.activities.map((item) => item.place_id), ['P2', 'P3'])
  assert.deepEqual(first.transport_segments, [segment('P2', 'P3', '公交')])

  const last = prepareActivityRemoval(day, 2)
  assert.deepEqual(last.activities.map((item) => item.place_id), ['P1', 'P2'])
  assert.deepEqual(last.transport_segments, [segment('P1', 'P2', '步行')])
})

test('删除中间项沿用相邻交通方式，新连接耗时未知', () => {
  const result = prepareActivityRemoval(day, 1)
  assert.deepEqual(result.activities.map((item) => item.place_id), ['P1', 'P3'])
  assert.deepEqual(result.transport_segments, [segment('P1', 'P3', '步行', null)])
})

test('目标无效或缺少相邻交通时拒绝构造', () => {
  assert.throws(() => prepareActivityRemoval(day, 3), /活动已变化/)
  assert.throws(() => prepareActivityRemoval({ ...day, activities: [activity('P1')] }, 0), /至少需要保留一项/)
  assert.throws(() => prepareActivityRemoval({ ...day, transport_segments: [] }, 1), /缺少相邻交通信息/)
})
