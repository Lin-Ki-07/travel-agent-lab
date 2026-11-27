import assert from 'node:assert/strict'
import { test } from 'node:test'
import { formatTransportMode, formatSegmentDuration, formatRouteDetails } from '../src/itineraryFormat.ts'

const segment = { from_place_id: 'P1', to_place_id: 'P2', mode: '步行', estimated_minutes: 99 }
const route = {
  status: 'ok', source: 'amap', queried_at: '2026-11-26T06:30:00+00:00',
  distance_meters: 180, duration_seconds: 121, parts: [], failure_reason: null,
}

test('成功路线按秒取整并显示距离、来源及北京时间', () => {
  const value = { ...segment, route }
  assert.equal(formatSegmentDuration(value), '预计 3 分钟 · 约 180 米')
  assert.equal(formatRouteDetails(value), '来源：高德；查询时间：2026-11-26 14:30（北京时间）')
  assert.equal(formatSegmentDuration({ ...segment, route: { ...route, distance_meters: 1250 } }),
    '预计 3 分钟 · 约 1.3 公里')
})

test('失败仅显示不可用，隐藏残留分钟和详细原因', () => {
  const value = { ...segment, route: { ...route, status: 'failed', distance_meters: null,
    duration_seconds: null, failure_reason: '公交查询缺少可靠城市编码，未查询路线' } }
  assert.equal(formatSegmentDuration(value), '该段路线不可用')
  assert.equal(formatRouteDetails(value), '')
})

test('旧行程显示未查询，不展示原估计或伪造来源', () => {
  for (const route of [undefined, null]) {
    assert.equal(formatSegmentDuration({ ...segment, route }), '该段路线未查询')
    assert.equal(formatRouteDetails({ ...segment, route }), '')
    assert.equal(formatSegmentDuration({ ...segment, route, estimated_minutes: null }), '该段路线未查询')
  }
})


test('所有行程的旧交通别名统一展示驾车', () => {
  for (const mode of ['打车', '出租车', ' TAXI ', '驾车']) assert.equal(formatTransportMode(mode), '驾车')
  assert.equal(formatTransportMode('公共交通'), '公共交通')
})
