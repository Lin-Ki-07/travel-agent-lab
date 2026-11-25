# v0.5.0 本地 API 契约

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
    "generated_at": "含时区的 ISO 8601 时间",
    "web_evidence": "本次检索的编号、标题、URL 和摘要；旧行程可能为空"
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
本次 `preferences` 留空时采用本地默认偏好；显式填写时以本次值为准。

## POST /api/plans/{plan_id}/save

无请求体。成功：200，返回 {"plan_id": "...", "saved": true}。
将当前进程中已生成且通过校验的行程写入独立的 `data/trips.db`；
不接收客户端回传的行程内容。重复保存同一 ID 不创建副本。

## GET /api/plans

返回 `{"plans":[...]}`，只列出已保存行程的摘要。每项含 plan_id、destination、
start_date、days、generated_at、saved_at，按保存时间倒序排列。

## GET /api/plans/{plan_id}

仅能读取已保存的行程。成功：200，返回与规划接口相同的
plan_id、itinerary 和 map_days 结构；map_days 从读取的行程重新派生。
未知或未保存的 ID 返回 404。

## DELETE /api/plans/{plan_id}

永久删除指定行程。已保存的行程从 `data/trips.db` 删除；当前进程中未保存的生成结果也可按 ID 删除。
成功返回 `{"plan_id":"...","deleted":true}`；ID 不存在返回 404。删除后列表与按 ID 读取不再返回该行程。
前端仅在归档面板中提供此操作，确认后执行；删除无法撤销。

## PUT /api/plans/{plan_id}/days/{day_number}

只编辑已保存行程的某一天。请求提供当天完整的 `activities` 和 `transport_segments`：

```json
{
  "activities": [{"place_id":"已有地点 ID","description":"参观","start_time":"09:00","end_time":"10:00"}],
  "transport_segments": []
}
```

地点必须来自该行程已有 `places`；活动时间不得重叠；相邻活动换地点时交通段必须按顺序连接。
成功返回更新后的 itinerary 和 map_days；无效内容返回 422 且原行程不变，未知行程返回 404。
编辑不查询新资料或调用模型；当天及总费用置为未知，旧天气、地点和网页资料仍为快照。

## GET /api/preferences、PUT /api/preferences

GET 返回 `{"preferences":["美食"]}`，未设置时为空列表。PUT 请求同一结构，
空列表可清除；最多 20 项，每项去除首尾空白后为 1–100 个字符。无效输入返回 422。
默认偏好与行程中本次实际采用的偏好分别保存，修改默认值不改写旧行程。

## POST /api/chat（v0.7.0 自然对话）

`core/chat_contract.py` 定义请求和响应结构。已生成行程的普通聊天消息
经此接口处理；明确的地点移除请求仍先走当前前端定位流程。

请求包含 `text`（本条用户消息）、可选 `plan_id`（当前行程）和 `history`
（按顺序排列的 `{role, content}`，role 只能为 `user` 或 `assistant`）。
响应以 `kind` 区分四种结果：

- `answer`：`{"kind":"answer","message":"..."}`，普通回答。
- `clarify`：`{"kind":"clarify","message":"..."}`，请求用户澄清。
- `edit_target`：含 `message` 和 `target`；`target` 指明从 1 开始的
  `day_number`、从 0 开始的 `activity_index` 及 `place_id`。后端用当前
  行程核对三者，目标不存在或不一致时返回 `clarify`，不修改行程。
- `edit_draft`：含 `message` 和 `draft` 的修改建议；`draft` 指明
  `plan_id`、生成时行程的 `source_fingerprint`、从 1 开始的 `day_number`、从 0 开始的 `activity_index`、
  `original_place_id`、`candidate_place_id`，以及拟替换当天的完整
  `activities` 和 `transport_segments`。

此协议检查响应的类型、必需字段和基本取值；确认接口还会按当前已保存行程重新核对地点、目标活动、时间、交通连接与行程指纹。`edit_draft` 不是保存指令；生成草案不写数据库，也不更新地图。

当前接口只返回 `answer`、`clarify` 或已核对的 `edit_target`，不会返回 `edit_draft`；模型输出非法
或模型调用失败返回 502。`plan_id` 未找到时返回 404。接口只读取行程，
不写数据库或更新地图。网页仍在本地内存保存聊天历史；未生成行程的新聊天
继续使用原需求解析流程，尚未接入此自然对话接口。

## 行程替换草案与确认（v0.7.0）

`POST /api/plans/{plan_id}/edit-draft` 接收 `day_number`、`activity_index`、`original_place_id` 和 `candidate_place_id`，生成内部草案并返回 `edit_draft`。Agent 只建议新活动描述；程序沿用原行程相邻交通方式，生成不写入。行程不存在返回 404；目标或候选无效返回 422；模型失败或响应不合规返回 502。

`POST /api/plans/{plan_id}/edit-draft/confirm` 接收前一步返回的 `draft` 对象，仅对已保存行程确认。后端重新核对草案与当前行程并条件更新，成功返回 `plan_id`、更新后的 `itinerary` 和 `map_days`；过期或非法草案返回 422，行程不存在返回 404。Web 选定候选后点击“确认替换”，依次调用这两个接口，不单独展示草案或交通方式。

## 错误

输入无效：422，返回 {"detail": "可读的具体原因"}。
请求体类型等由 FastAPI 校验的错误可能返回 detail 数组，前端同时支持字符串和数组。
地点、天气、网页资料或模型服务失败：502，返回
{"detail": "可读的具体原因"}。不在响应中返回密钥。
未知或未保存的 plan_id：404。

## 保存边界

已保存行程跨后端重启有效，未保存生成结果仅在当前进程暂存。
数据库位于被 Git 忽略的 `data/trips.db`，与 CLI 记忆数据库分开；记录含 `schema_version=1`。
本版支持按 ID 删除行程；没有账号或多用户隔离。

网页聊天标题、消息和草稿只保留在页面内存中。刷新后可通过列表与 GET 重新打开已保存行程，
不会恢复完整聊天或未保存草稿；重启后端不主动清除页面已有快照。

## 验证状态

29 个离线 unittest 通过。真实浏览器案例已完成生成、保存、后端重启、刷新后重新打开和编辑地点；
后端 GET 读回首站“九峰公园”，地图首站及六项顺序与行程一致。编辑后活动描述仍写着原先的室内展馆，
用户选择暂不处理。没有自动化浏览器测试或量化效果评测。
Swagger UI 可以手动复现接口调用；执行解析或规划接口会产生真实外部调用和潜在费用。
