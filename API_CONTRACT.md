# v0.4.0 本地 API 契约

仅供本地单用户使用。请求和响应均为 JSON，日期使用 YYYY-MM-DD，
时间使用 HH:MM，经纬度分别使用 latitude、longitude 数值。

## POST /api/plans

请求字段：destination、start_date、days（或 end_date）、travelers、
budget_cny、preferences。前端传字符串，与现有 parse_trip_request
的输入格式一致；preferences 为逗号分隔字符串。

成功：200，返回：
{
  "plan_id": "服务端生成的不透明 ID",
  "itinerary": {
    "request": {},
    "places": [],
    "daily_plans": [],
    "estimated_total_cny": null,
    "generated_at": "含时区的 ISO 8601 时间"
  }
}

itinerary 由现有规划与校验流程生成。places 保留高德 place_id、
name、address、latitude、longitude、source、queried_at；
daily_plans 保留日期、按顺序排列的 activities、transport_segments、
weather 和费用字段。地图按每天 activities 的顺序，通过 place_id
关联 places；相邻不同地点的坐标连线标注为“地点顺序示意线”，
不代表实际道路路线。

生成成功后的行程暂存在当前服务进程内，但尚未标记为“已保存”。

## POST /api/plans/{plan_id}/save

无请求体。成功：200，返回 {"plan_id": "...", "saved": true}。
仅将当前进程中已生成且通过校验的行程标记为已保存；
不接收客户端回传的行程内容，不提供修改。

## GET /api/plans/{plan_id}

仅能读取已保存的行程。成功：200，返回与规划接口相同的
plan_id 和 itinerary 结构。未知或未保存的 ID 返回 404。

## 错误

输入无效：422，返回 {"detail": "可读的具体原因"}。
地点、天气、网页资料或模型服务失败：502，返回
{"detail": "可读的具体原因"}。不在响应中返回密钥。
未知或未保存的 plan_id：404。

## 保存边界

保存只在当前后端进程的内存中有效；重启后读取旧 ID 返回 404。
本版没有编辑、删除、账号、跨进程同步或跨重启持久化。
v0.5.0 再设计持久化与编辑。