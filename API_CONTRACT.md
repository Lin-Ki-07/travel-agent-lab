# v0.4.0 本地 API 契约

仅供本地单用户使用。请求和响应均为 JSON，日期使用 YYYY-MM-DD，
响应中的活动时间由 jsonable_encoder 输出为 HH:MM:SS（当前业务输入使用分钟精度），
日期时间使用包含时区的 ISO 8601 字符串。地点经纬度分别使用 latitude、longitude 数值。

## 本地入口

- `GET /`：返回服务名称、前端地址和文档入口。
- `GET /docs`：FastAPI 自动生成的 Swagger UI，可手动调用接口。
- `GET /redoc`：接口阅读页面；`GET /openapi.json`：机器可读接口定义。

这些是 HTTP 路由，不生成本地 docs 文件夹。通过 Vite 的 `/api` 代理调用业务接口。

## POST /api/plans/parse

只解析自然语言需求，不查询旅行资料、不生成行程、不保存。会调用模型。

请求示例：

```json
{"text": "我想去杭州玩两天，美食为主"}
```

成功：200，示例响应（识别内容取决于模型）：

```json
{
  "fields": {
    "destination": "杭州",
    "start_date": "",
    "days": "2",
    "end_date": "",
    "travelers": "",
    "budget_cny": "",
    "preferences": "美食"
  },
  "missing": ["start_date"],
  "issues": [],
  "summary": "杭州，2 天，偏好：美食"
}
```

fields 的七个字段始终为字符串；缺失字段补空串，多余模型字段丢弃。
missing 标出 destination、start_date 或 days（天数与结束日期均缺失时）；
必填完整后，复用 parse_trip_request 检查并在 issues 返回问题。
存在缺失或问题时仍可返回 200，由用户补齐并确认表单；这不表示请求已可用于规划。
相对日期以北京时间（UTC+8）为准，每次只解析本次输入，不携带聊天历史。
空文本或不可解析的模型 JSON 返回 422，模型请求失败返回 502。

## POST /api/plans

请求字段：destination、start_date、days（或 end_date）、travelers、
budget_cny、preferences。前端传字符串，与现有 parse_trip_request
的输入格式一致；preferences 为逗号分隔字符串。

成功：200，返回以下结构示意（request、places、daily_plans 的字段见 core/trip_models.py）：

```json
{
  "plan_id": "服务端生成的不透明 ID",
  "itinerary": {
    "request": {},
    "places": [],
    "daily_plans": [],
    "estimated_total_cny": null,
    "generated_at": "含时区的 ISO 8601 时间"
  },
  "map_days": [
    {
      "day_number": 1,
      "plan_date": "YYYY-MM-DD",
      "stops": [
        {
          "order": 1,
          "place_id": "高德地点 ID",
          "name": "地点名称",
          "position": [120.15, 30.25]
        }
      ],
      "line": {
        "kind": "place_order_schematic",
        "label": "地点顺序示意线，非实际道路路线",
        "positions": [[120.15, 30.25]]
      }
    }
  ]
}
```

itinerary 由现有规划与校验流程生成。places 保留高德 place_id、
name、address、latitude、longitude、source、queried_at；
daily_plans 保留日期、按顺序排列的 activities、transport_segments、
weather 和费用字段。地图按每天 activities 的顺序，通过 place_id
关联 places；相邻不同地点的坐标连线标注为“地点顺序示意线”，
不代表实际道路路线。
position 和 line.positions 中的坐标顺序均为 [经度, 纬度]；
按 stops.order 绘制标记，按 line.positions 绘制折线，并显示 line.label。

生成成功后的行程暂存在当前服务进程内，但尚未标记为“已保存”。

## POST /api/plans/{plan_id}/save

无请求体。成功：200，返回 {"plan_id": "...", "saved": true}。
仅将当前进程中已生成且通过校验的行程标记为已保存；
不接收客户端回传的行程内容，不提供修改。

## GET /api/plans/{plan_id}

仅能读取已保存的行程。成功：200，返回与规划接口相同的
plan_id、itinerary 和 map_days 结构；map_days 与规划时相同。
未知或未保存的 ID 返回 404。

## 错误

输入无效：422，返回 {"detail": "可读的具体原因"}。
请求体类型等由 FastAPI 校验的错误可能返回 detail 数组，前端同时支持字符串和数组。
地点、天气、网页资料或模型服务失败：502，返回
{"detail": "可读的具体原因"}。不在响应中返回密钥。
未知或未保存的 plan_id：404。

## 保存边界

保存只在当前后端进程的内存中有效；重启后读取旧 ID 返回 404。
本版没有编辑、删除、账号、跨进程同步或跨重启持久化。
v0.5.0 再设计持久化与编辑。

网页聊天标题、消息和草稿与后端行程分开，只保留在页面内存中。左侧聊天切换不调用
GET 读取接口，刷新页面会失去聊天列表；重启后端不主动清除前端已有快照。

## 验证状态

开发中用临时 TestClient 模拟脚本验证了规划成功、422/502、未保存与未知 ID 的 404、
保存后读取一致及 map_days 顺序。真实服务上的生成、保存、读取和重启失效联合验收暂缓。
Swagger UI 可以手动复现接口调用；执行解析或规划接口会产生真实外部调用和潜在费用。
