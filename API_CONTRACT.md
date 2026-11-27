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
name、address、latitude、longitude、source、queried_at，以及可选 citycode；
citycode 仅保留高德 POI 返回的非空 ASCII 数字字符串（保留前导零），缺失或异常为 null；
旧记录缺字段按 null 读回，不从城市名或 adcode 推导；
daily_plans 保留日期、按顺序排列的 activities、transport_segments、
weather 和费用字段。地图按每天 activities 的顺序，通过 place_id
关联 places；相邻不同地点的坐标连线标注为“地点顺序示意线”，
不代表实际道路路线。
position 和 line.positions 中的坐标顺序均为 [经度, 纬度]；
按 stops.order 绘制标记。map_days 新增可选 segments，按相邻不同地点的活动顺序排列：
每项含 from_order、to_order、kind、parts、fallback_positions。
kind 为 route_snapshot 时，parts 保留快照中每个 mode 与 positions；各 part 独立绘制，不跨 part 连接。
kind 为 place_order_schematic 时 parts 为空；fallback_positions 和原 line 仅为后端兼容字段，前端不绘制示意连线。
失败、无快照或几何损坏时仅保留地点标记；旧响应没有 segments 时也只保留标记。
成功段按 parts 独立绘制，不跨 part 连接；步行绿色、驾车蓝色、公交紫色实线。
交通行对失败显示“该段路线不可用”，无快照显示“该段路线未查询”，隐藏原估计及失败详情；failure_reason仍保留于响应。成功继续显示距离、耗时、来源和查询时间。
地图展示已有快照不会触发路线查询。两端地点均有 citycode 时公交已接通查询，但真实公交端到端尚未验收。

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
编辑不调用模型，不刷新地点、天气或网页资料；校验后会复用未变路线并查询需要更新的路段，可能增加高德请求及串行等待时间。当天及总费用置为未知。普通单日保存仍沿用原有更新方式，没有新增客户端指纹协议。

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

`POST /api/chat` 当前返回 `answer`、`clarify` 或已核对的 `edit_target`，不会在普通对话响应中返回 `edit_draft`；模型输出非法或模型调用失败返回 502。`plan_id` 未找到时返回 404。该接口只读取行程，不写数据库或更新地图。网页仍在本地内存保存聊天历史；未生成行程的新聊天继续使用原需求解析流程，尚未接入此自然对话接口。

## 行程替换草案与确认（v0.7.0）

`POST /api/plans/{plan_id}/edit-draft` 接收 `day_number`、`activity_index`、`original_place_id` 和 `candidate_place_id`，生成内部草案并返回 `edit_draft`。Agent 只建议新活动描述；程序沿用原行程相邻交通方式，生成不写入，也不查询交通路线。行程不存在返回 404；目标或候选无效返回 422；模型失败或响应不合规返回 502。

`POST /api/plans/{plan_id}/edit-draft/confirm` 接收前一步返回的 `draft` 对象，仅对已保存行程确认。后端先核对草案与当前行程，再更新编辑日路线，最后按原 source_fingerprint 条件更新；查询期间行程若变化则返回 422，不覆盖其他修改（已经发生的查询不会撤销）。成功返回 `plan_id`、更新后的 `itinerary` 和 `map_days`；过期或非法草案返回 422，行程不存在返回 404。Web 选定候选后点击“确认替换”，依次调用这两个接口，不单独展示草案或交通方式。

## 错误

输入无效：422，返回 {"detail": "可读的具体原因"}。
请求体类型等由 FastAPI 校验的错误可能返回 detail 数组，前端同时支持字符串和数组。
地点、天气、网页资料或模型服务失败：502，返回
{"detail": "可读的具体原因"}。不在响应中返回密钥。
未知或未保存的 plan_id：404。

## 保存边界

### v0.8.0 路线快照与生成、编辑边界

交通段新增可选 `route`，旧行程缺失此字段时按 `null` 读取，表示未查询。
非空快照含 `status`（`ok` 或 `failed`）、`source`、带时区的 `queried_at`、
`distance_meters`、`duration_seconds`、`parts`、`failure_reason`。
成功快照的距离和秒数必须为正整数，失败原因为 null；`parts` 至少一项，
每项含非空 `mode` 及至少两个 `[经度, 纬度]` 有限坐标的 `positions`。
失败快照必须有非空原因，距离和秒数为 null，parts 为空。
有成功快照时 `estimated_minutes` 必须等于秒数向上取整到分钟；失败时为 null。

新行程生成并校验后，后端逐段查询明确的步行、驾车方式，失败不阻断整份行程。
公共交通段在两端地点均有 citycode 时查询，传入两端编码及当天行程日期；缺编码或方式未支持时不发请求，返回带原因的失败快照。
成功预计分钟数来自路线秒数；失败清除原模型估计耗时。生成接口由此新增高德请求，
当前逐段串行查询，不自动重试。GET 和 /save 不重新查询；单日编辑与替换确认按下述规则更新路线。
地图按成功快照的 parts 绘制路线，失败或无快照仅保留地点标记，不绘制示意线；不重新查询。
模型生成结果和单日编辑请求中的 route 不作为可信事实接受。编辑先由 edit_day 重建并校验，再由后端从旧行程复用快照或发起查询：

- 同一编辑日内，起终点 ID 和归一化交通方式相同且旧 route 非空时，复用旧成功或失败快照，保留其原查询时间及对应分钟数；描述或活动时间变化不会触发重新查询。复用不代表实时交通信息。
- 新连接、端点或方式变化、旧 route 缺失时，清除输入快照和旧分钟数，按当前方式查询；成功按秒数向上取整，失败分钟数为 null。
- 删除中间活动形成的新连接不能复用被删除地点两侧路线；剩余原连接可复用。无交通段时不查询，其他天不重新查询。
- 公共交通待查询段在两端均有 citycode 时发起一次查询，传入当天行程日期；缺编码及不支持的方式不请求，生成带原因的失败快照。
- 草案生成不查询路线、不写数据库；替换确认在草案校验后更新路线，最终指纹条件写入保护保持不变。

旧行程原有 estimated_minutes 仍保留，但不能视为高德查询结果。
新增字段存于原 JSON，schema_version 仍为 1；旧版本程序不保证保留新字段。

已保存行程跨后端重启有效，未保存生成结果仅在当前进程暂存。
数据库位于被 Git 忽略的 `data/trips.db`，与 CLI 记忆数据库分开；记录含 `schema_version=1`。
本版支持按 ID 删除行程；没有账号或多用户隔离。

网页聊天标题、消息和草稿只保留在页面内存中。刷新后可通过列表与 GET 重新打开已保存行程，
不会恢复完整聊天或未保存草稿；重启后端不主动清除页面已有快照。

## 验证状态

截至 8.2.3.2，74 个后端离线 unittest 通过（路线服务和模型均使用模拟）；git diff --check 通过。新增验证覆盖编辑路线复用、变更重查、保存读回、草案不查询及查询期间并发更新拒绝覆盖。真实路线接口及编辑后的真实浏览器路线行为尚未验收。

历史真实浏览器案例已完成生成、保存、后端重启、刷新后重新打开和编辑地点；
后端 GET 读回首站“九峰公园”，地图首站及六项顺序与行程一致。编辑后活动描述仍写着原先的室内展馆，
用户选择暂不处理。没有自动化浏览器测试或量化效果评测。
Swagger UI 可以手动复现接口调用；执行解析或规划接口会产生真实外部调用和潜在费用。


### v0.8.0 验收补充

当前81项后端、10项前端离线测试通过。模拟浏览器检查覆盖实线方式配色、局部失败回退、日期切换及候选组件点选；一条真实步行查询成功并完成道路底图对照。项目作者报告新生成行程显示、保存及刷新读回正常，未提供该次详细快照。真实驾车/公交与编辑重查尚未单独验收；公交城市编码和旧行程主动刷新未实现。以上补充优先于历史步骤的待验状态，不表示版本已发布。


### 8.2.3.5a 公共交通查询接入补充

明确方式公交、公交车、公共交通、地铁、bus、subway、metro、transit统一调用公共交通接口，保留原方式文本；归一化兼容大小写及首尾空白。按接口返回顺序选首个距离、耗时和分段几何均通过校验的公共交通方案，跳过损坏及暂不支持的方案；每段单次查询、不重试、不自动改成打车；标为地铁不保证返回方案只含地铁。铁路/出租车混合或几何不完整仍返回失败。尚无地铁优先、合理性筛选或有限替代查询策略。既有失败快照继续复用，不自动补全旧行程。90项后端离线测试通过，真实公交响应、城市编码有效性和端到端未验收。


8.2.3.5b补充：所有公交方案均不可用时返回无距离、耗时和几何的失败快照；不拼接残缺方案。步行及驾车仍取第一条方案。92项后端离线测试通过，未新增网络请求，真实公交兼容性仍待验收。


### 8.2.3.5c 公共交通地铁偏好（当前规则）

同一次公交请求将AlternativeRoute设为5，最多返回5条方案；不增加请求次数。先排除距离、耗时或几何无效的方案，再取耗时最短者作为基准。实际采用的首条busline的type为“地铁线路”时判为含地铁方案，不根据名称猜测。含地铁方案相对基准额外耗时同时不超过900秒且不超过25%时优先，多个符合者取耗时最短；无符合者取全部可用方案中耗时最短者，同类耗时相同保持接口顺序。类型缺失仍作为普通公共交通候选。以上替代此前首个可用方案规则，尚无步行距离、换乘上限或方式替代。93项后端离线测试通过，真实公交未验收。


### 8.2.3.5d 有上限的交通替代查询（2026-11-27）

仅公共交通段启用替代：起终点球面直线距离不超过800米时先查步行，真实步行距离不超过1200米且耗时不超过1200秒则采用；否则查公共交通。公共交通明确无可用方案或缺城市编码时最多再查一次驾车道路，成功将方式改为“打车”；步行替代成功改为“步行”。明确步行、打车及自驾只查原方式。直线距离只用于查询选择，不展示为道路距离。每段至多3次请求，非短距离至多2次，不重试，不新增车费或接驾耗时。

RouteSnapshot末尾新增可选failure_kind：no_route表示明确无可用方案；blocked表示权限、配额、参数或其他服务拒绝；unavailable表示超时、网络或响应异常。旧快照缺字段读回None。失败分类不通过原始错误文本判断；只有no_route允许继续替代，blocked、unavailable及未知分类停止。缺城市编码直接跳过公交请求；非路线计算类拒绝保守停止。失败仍无距离、耗时和几何；全部失败保留原方式并显示不可用。生成和编辑待查询段共用规则，已有快照复用不变，旧行程不会自动补全。

本步局部修改core/trip_routes.py、core/trip_models.py、tools/amap_route_tool.py、web/src/types.ts及对应离线测试；96项后端离线测试、前端build和git diff --check通过。测试禁用dotenv并阻止真实HTTP请求，覆盖阈值边界、调用顺序和上限、明确方式保持、错误停止、失败分类往返及旧快照兼容。未改Agent代码或新增UI入口，未读取环境文件、调用真实业务服务或修改业务数据库。真实业务验收、旧行程补全入口及公交步行/换乘约束仍未完成。


### 8.2.3.6a 已保存行程主动补全交通（2026-11-27）

新增POST /api/plans/{plan_id}/routes/complete，无请求体，仅处理已保存行程，未知ID返回404。整份行程仅补查失败或无快照的交通段，成功快照保留；沿用当前方式策略及每段至多3次请求，不调用模型或补查地点编码。查询后按原行程指纹条件保存，期间发生修改或删除返回409，不覆盖并发结果，已发生的查询无法撤销。成功返回plan_id、itinerary、map_days，仍失败的段保存失败快照。

已保存行程详情交通区域新增“补全交通”，执行时禁用并显示“补全中…”，编辑表单打开时禁用，当前编辑保存与补全互斥。成功保存后才更新展示；打开、刷新或普通保存不自动补查。缺城市编码的旧公交段仍只能按既有步行/打车替代策略处理，不代表旧公交编码恢复。

局部修改core/trip_routes.py、api.py、core/trip_store.py及前端API/App/行程组件，新增tests/test_route_completion.py。旧JSON指纹比较补齐citycode与failure_kind默认值，避免新增可选字段导致旧记录误报冲突，保留原事务及原JSON条件更新。99项后端离线测试、10项前端测试、build、lint和git diff --check通过；覆盖成功不查、失败/缺失查询、旧JSON保存读回、并发编辑拒绝覆盖及404不查询。测试禁用dotenv和真实HTTP请求，业务数据库未修改，未调用真实服务或修改Agent。按钮状态仅代码检查及类型构建通过，真实浏览器交互尚未验收。


### 全部行程统一驾车语义（2026-11-27）

本规则适用于所有目的地和地图，青岛仅为此前验收案例。TransportSegment在构造及旧记录读回时将打车、出租车、taxi（忽略大小写与首尾空白）归一为驾车；公共交通替代道路成功也写驾车。前端兼容旧响应统一展示驾车。现有真实几何及成功快照复用规则不变，不批量改写业务数据库；打开、刷新不自动查询，旧缺失或失败段由补全交通显式触发。

局部修改core/trip_models.py、core/trip_routes.py、core/trip_store.py及前端格式化/展示与测试。条件写入的旧记录指纹同步归一交通别名，避免旧别名读回后误报冲突。100项后端、11项前端测试、build、lint及git diff --check通过，含旧taxi记录读取不写库及条件保存测试。验证禁用dotenv和真实HTTP请求，未调用真实业务或修改业务数据库、Agent功能。前述打车表述作为历史记录保留，当前统一称驾车，不代表真实公交或所有城市均已实测。
