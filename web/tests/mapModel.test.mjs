import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildOverlaySpec, clampDayIndex } from '../src/mapModel.ts'

const a = [120, 30], b = [120.1, 30.1], c = [120.2, 30.2]
const stops = [a, b, c].map((position, index) => ({
  order: index + 1, place_id: `P${index}`, name: `地点${index}`, position,
}))
const day = { day_number: 1, plan_date: '2026-11-26', stops,
  line: { kind: 'place_order_schematic', label: '旧示意线', positions: [a, b, c] } }
const segment = { from_order: 1, to_order: 2, kind: 'route_snapshot',
  parts: [{ mode: 'walking', positions: [a, b] }], fallback_positions: [a, b] }

test('每个 part 独立绘制并按方式配色，不跨 part 拼接或叠加整天线', () => {
  const parts = ['walking', 'driving', 'transit'].map((mode, i) => ({ mode,
    positions: [[120 + i / 10, 30], [120.05 + i / 10, 30.05]] }))
  const spec = buildOverlaySpec({ ...day, segments: [{ ...segment, parts }] })
  assert.equal(spec.lines.length, 3)
  assert.deepEqual(spec.lines.map(l => l.path), parts.map(p => p.positions))
  assert.deepEqual(spec.lines.map(l => l.color), ['#238636', '#2a71d3', '#8957b5'])
  assert.ok(spec.lines.every(l => !l.dashed))
  assert.equal(spec.markers.length, 3)
})

test('局部失败只回退该交通段，全失败仍保留全部连接', () => {
  const failed = { ...segment, from_order: 2, to_order: 3,
    kind: 'place_order_schematic', parts: [], fallback_positions: [b, c] }
  const spec = buildOverlaySpec({ ...day, segments: [segment, failed] })
  assert.deepEqual(spec.lines.map(l => l.dashed), [false, true])
  assert.deepEqual(spec.lines[1].path, [b, c])
  assert.ok(spec.label.includes('灰色虚线'))
  assert.ok(buildOverlaySpec({ ...day, segments: [failed, failed] }).lines.every(l => l.dashed))
})

test('坏坐标或未知方式令整条交通段回退，不删坏点后误连', () => {
  for (const part of [
    { mode: 'walking', positions: [a, [NaN, 30], b] },
    { mode: 'walking', positions: [a] },
    { mode: 'railway', positions: [a, b] },
  ]) {
    const spec = buildOverlaySpec({ ...day, segments: [{ ...segment, parts: [segment.parts[0], part] }] })
    assert.equal(spec.lines.length, 1)
    assert.equal(spec.lines[0].dashed, true)
    assert.deepEqual(spec.lines[0].path, [a, b])
  }
})

test('旧地图响应兼容，空交通段不画线，日期索引保持原行为', () => {
  assert.deepEqual(buildOverlaySpec(day).lines[0].path, [a, b, c])
  assert.equal(buildOverlaySpec({ ...day, segments: [] }).lines.length, 0)
  assert.equal(buildOverlaySpec({ ...day, stops: [stops[0]], segments: [] }).markers.length, 1)
  assert.equal(clampDayIndex(4, 2), 1)
  assert.equal(clampDayIndex(0, 0), 0)
})
