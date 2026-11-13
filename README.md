# Travel Agent Lab

一个本地单用户旅行规划项目：React 网页通过 FastAPI 调用 Python 规划流程，根据高德地点、wttr.in 天气和 Tavily 网页资料生成经程序校验的逐日行程，并在高德地图上按天展示地点与顺序示意线。保留命令行 ReAct、Web RAG、多轮对话和 SQLite 长期记忆。

当前开发阶段为 **v0.4.0：本地前后端与高德地图**，代码位于开发分支；版本号是学习阶段编号，不代表已合入 main、创建标签或发布 Release。保存读取及重启边界的真实服务联合验收仍待补充。

## 当前能力

- FastAPI 提供自然语言需求解析、行程规划、当前进程内保存和按 ID 读取接口；详见 [API 契约](API_CONTRACT.md)。
- React + TypeScript + Vite 前端支持需求表单、解析填表、生成中和失败状态、逐日结果、三栏拖动及聊天切换。
- 新聊天立即创建卡片，默认“新的旅游规划”；解析出目的地后自动命名，也可右键重命名。手动标题不被自动覆盖。
- 高德 JS API 按后端 map_days 的日期、地点和顺序绘制编号标记与示意线；不请求实际道路路径。
- 文本 ReAct 循环：模型输出 Action，Python 解析并执行工具，将 Observation 回传模型。
- 天气查询：wttr.in；旅行网页证据搜索：Tavily，保留来源编号、标题、URL 和文本。
- 函数和工具对象注册，函数签名绑定检查，执行耗时和结果记录。
- 结构化 Message、Agent 抽象基类、独立的 AgentConfig 与 LLMConfig。
- OpenAI 兼容模型客户端、模型调用异常处理、工具请求超时。
- 连续对话，按完整轮次裁剪旧历史；模型调用失败或步数耗尽时恢复本轮开始前的历史。
- SQLite 记忆新增、读取、字面关键词搜索、更新、删除和最近记录列表。
- 直接记忆命令不调用模型；MemoryTool 为 Agent 提供同一套存储能力。
- `/plan` 收集目的地、出发日期、天数或结束日期、人数、全程预算和偏好；先校验请求，再查询高德地点、wttr.in 逐日天气和 Tavily 网页证据。
- 规划模型输出 JSON，经解析后检查天数与日期、真实地点 ID、活动时间顺序、交通段连接、每日费用与总额；非法输出最多重试一次。
- 逐日命令行输出保留地点 ID、坐标、来源和查询时间；无可用预报、未知费用与未知交通耗时明确标注。

当前为本地单用户原型，先支持单目的地、短途多日。网页聊天、草稿和历史列表只存在当前页面内存中，刷新后清空；后端行程与保存标记只存在当前服务进程内，重启后失效。CLI 长期记忆保存在被忽略的 `data/memory.db`，与网页行程保存是不同能力。多 provider 配置不代表已逐一验证所有服务。

## 快速开始

需要 Python 3.10 或更高版本。请从项目根目录执行命令，因为提示词使用相对路径读取。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

当前 `requirements.txt` 没有锁定依赖版本。此前环境中出现过 HTTP 解压依赖兼容问题；已在学习过程中使用的修复方案是：

```powershell
python -m pip install "openai>=1,<2" "httpx>=0.27,<0.29"
```

这是一项已知的复现限制，后续需要整理可复现的依赖清单。

在根目录创建 `.env`，填写自己服务商提供的有效模型标识和密钥：

```dotenv
LLM_PROVIDER=deepseek
MODEL_ID=填写服务商支持的模型标识
DEEPSEEK_API_KEY=填写自己的密钥
OPENAI_BASE_URL=https://api.deepseek.com
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7
AGENT_MAX_STEPS=5
AGENT_MAX_HISTORY_MESSAGES=20
TAVILY_API_KEY=填写自己的密钥
AMAP_API_KEY=填写自己的高德 Web 服务 Key
```

DeepSeek 专用密钥为空时，配置会回退读取 `OPENAI_API_KEY`。显式设置的 `OPENAI_BASE_URL` 优先于 provider 默认地址，切换服务商时应同步调整。`.env` 已加入忽略规则，不要提交真实凭证。

### 本地网页运行

前端需要兼容当前 Vite 版本的 Node.js 与 npm；安装依赖前可查看 `web/package-lock.json` 中的 engines 要求。首次在根目录安装前端依赖：

```powershell
npm --prefix web ci
```

在 `web/.env.local` 配置独立的高德 **Web端（JS API）** Key，示例与说明见 [前端运行文档](web/README.md)。后端 `AMAP_API_KEY` 是 Web 服务 Key，不要复制进前端配置。

开两个 PowerShell 窗口，均从仓库根目录执行；Python 窗口如使用虚拟环境，先激活环境。

窗口一，启动后端：

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

窗口二，启动前端：

```powershell
npm --prefix web run dev -- --host 127.0.0.1 --port 5173
```

打开 [旅行页面](http://127.0.0.1:5173)。后端 [首页](http://127.0.0.1:8000) 提供入口说明；[Swagger UI](http://127.0.0.1:8000/docs) 可调试接口，[ReDoc](http://127.0.0.1:8000/redoc) 可阅读接口文档。`/docs` 是网页路由，不会生成本地 docs 文件夹。Vite 把 `/api` 代理到 8000，当前开发方式不需要跨域配置。若端口被占用，以终端实际显示的地址为准。

两个进程均需保持运行；关机后重新启动。修改环境变量后重启相应进程。后端使用一个工作进程，避免内存中的行程分散到多个进程。自然语言解析会调用模型，但不会自动规划；确认表单后点击“生成行程”才会查询外部资料并调用规划模型，两类请求均可能产生费用。

### 命令行运行

```powershell
python main.py
```

启动后直接输入旅行问题，或使用以下命令：

| 命令 | 用途 |
| --- | --- |
| `/remember 内容` | 保存长期记忆 |
| `/memories` | 查看最近创建的 10 条记忆 |
| `/recall 关键词` | 字面关键词搜索，最多返回 10 条 |
| `/update 完整ID 新内容` | 更新指定记忆，保留 ID 和创建时间 |
| `/forget 完整ID` | 删除指定记忆 |
| `/memory-help` | 查看记忆命令帮助 |
| `/history` | 查看当前对话消息 |
| `/plan` | 逐项填写需求，生成结构化逐日行程 |
| `/new` | 清空对话历史，保留长期记忆 |
| `/quit` | 退出程序 |

部分明确的自然语言列表请求，例如“我保存的长期记忆是什么？”，也会直接查询数据库。这是固定表达匹配，不是通用意图识别。未知斜杠命令返回帮助，不进入 Agent。

记忆命令不调用模型；普通旅行请求进入 ReAct。`/plan` 按提示填写目的地和出发日期，并在旅行天数、结束日期中只填一项；人数默认 1，预算和偏好可留空。预算单位为人民币，口径是全程所有同行者合计。规划会调用外部服务和模型，可能产生费用。程序启动会初始化模型客户端，因此仍需可用的模型配置；初始化不等于发起模型请求。

历史消息默认软上限为 20 条，可通过 `AGENT_MAX_HISTORY_MESSAGES` 调整。超限时删除最早的完整轮次，但保留当前轮次，因此不是严格的消息或 token 上限。

## 代码结构

```text
main.py                         组装配置、客户端、工具和 Agent
api.py                          FastAPI 首页、需求解析、规划、保存与读取
API_CONTRACT.md                 前后端接口契约
web/                            React + TypeScript + Vite 页面
commands/
  memory_commands.py            直接记忆命令及固定表达分流
  trip_commands.py              规划请求的命令行输入
  trip_output.py                逐日行程文本输出
core/
  config.py                     AgentConfig、LLMConfig 与环境变量解析
  exceptions.py                 LLMError
  itinerary_validator.py        模型 JSON 解析与行程校验
  llm_client.py                 消息转换与模型请求
  message.py                    消息数据结构
  planning_context.py           规划模型的事实上下文
  trip_input.py                 输入解析与默认值
  trip_models.py                请求、地点、天气和行程数据结构
  trip_planner.py               模型生成与有限重试
  trip_sources.py               高德、天气和 Web RAG 资料获取
  trip_service.py               CLI 与 API 共用的规划入口
  trip_parser.py                自然语言解析填表，日期基准为北京时间
  map_view.py                   从已校验活动生成逐日地图数据
memory/
  item.py                       MemoryItem 记忆数据结构
  sqlite_store.py               SQLite 存储、检索与维护
agents/
  base.py                       公共接口与历史管理
  react_agent.py                ReAct 循环与文本 Action 解析
tools/
  base.py                       工具抽象基类
  registry.py                   注册、签名检查、描述、执行记录
  weather_tool.py               天气函数及 WeatherTool 包装类
  attraction_tool.py            景点搜索函数
  amap_place_tool.py            高德地点搜索
  trip_weather_tool.py          wttr.in 逐日预报
  memory_tool.py                供 Agent 调用的记忆工具
prompts/
  system_prompt.md              含工具占位符的提示词模板
tests/
  test_trip_flow.py             规划流程固定离线案例
  test_itinerary_json.py        模型 JSON 围栏与外围文字清理
  test_trip_parser.py           自然语言解析固定离线案例
```

## 数据流与校验边界

1. 网页发送需求文本到 `/api/plans/parse`；模型提取字符串字段，后端整理缺失项与问题，前端填入表单等待确认。相对日期以北京时间（UTC+8）为准，每次解析只使用本次输入，不自动携带整段聊天历史。
2. 确认表单后，网页通过 Vite 代理调用 `/api/plans`。API 调用共用 `plan_trip`，复用 CLI 的请求解析、高德地点查询、天气查询、Tavily 检索和模型规划。
3. 模型输出经 JSON 格式清理和原有行程校验；检查日期、地点 ID、活动时间、交通段连接及预算内部一致性。非法输出最多重试一次，仍不合法则返回失败。
4. 后端从通过校验的活动列表派生 `map_days`；前端只按这些数据绘制，坐标顺序为 `[经度, 纬度]`。示意线不证明实际道路、距离或耗时。
5. 保存接口只把服务端已生成的 ID 标记为已保存；读取接口只接受已保存的 ID。左侧切换聊天使用页面缓存，不会请求读取接口。

程序校验保证结构与内部一致性，不能证明开放时间、交通方式、费用估算或模型摘要的现实准确性；真实地点 ID 也不代表行程安排一定可执行。

## 如何验证

语法检查不会发起外部请求：

```powershell
python -m compileall -q agents core tools memory commands main.py api.py
```

规划固定案例运行：

```powershell
python -m unittest discover -s tests -v
npm --prefix web run build
npm --prefix web run lint
```

当前 21 个离线 unittest 覆盖规划流程（4）、JSON 清理（6）和自然语言解析（11）；前端构建含 TypeScript 检查，lint 单独运行。开发中还用临时模拟脚本验证 API 的 200/422/502、未保存与未知 ID 的 404、保存后读回一致，以及地图日期、顺序、重复地点处理；这些临时脚本未作为测试文件入库。

项目作者报告浏览器自然语言填表、地图按天与地点顺序、三栏拖动、新聊天及重命名通过；目前没有自动化浏览器测试或本版真实流程输出留档供独立复核。真实服务上的“生成 → 保存 → GET 读取 → 重启后旧 ID 返回 404”联合验收已暂缓，不能用左侧缓存切换代替。尚无量化成功率、延迟或成本评测。

## 当前限制

- 关键词搜索是字面包含匹配，英文区分大小写，不理解同义表达；列表按创建时间排序，更新不改变创建时间。
- 记忆不会自动注入每次请求。普通旅行任务是否检索记忆由模型结合提示词决定。
- 直接记忆命令不写入对话历史；更新或删除数据库不会同步清除历史中的旧信息。需要排除旧上下文时使用 `/new`。
- 失败历史恢复仅覆盖 `LLMError` 和步数耗尽，不撤销数据库写入、工具请求、执行记录或费用。
- 模型对记忆工具的写入行为依赖提示词，尚无独立的授权校验；执行记录中的 success 表示函数执行未抛异常，不保证业务成功。
- 无多用户隔离、自动总结或 TTL 遗忘；依赖未锁版本，`Ctrl+C` 和输入结束的退出处理暂缓完善。
- 规划校验检查结构及内部一致性，不证明活动开放时间、交通方式或费用估算的现实准确性；费用未知时总额保持未知，不能据此判断符合预算。
- wttr.in 仅在返回的日期范围内提供预报；范围外显示暂无可用预报。缺少资料或外部服务失败时，规划给出错误或限制说明。
- 普通 ReAct 对话的历史与记忆不会自动注入网页或 `/plan` 的规划流程；网页输入框用于解析单次需求，并非通用多轮 Agent。
- 行程保存仅限进程内，前端刷新丢失聊天；重启后端不会主动清空前端缓存，旧内容仍可显示，但不代表服务端仍可读取。未实现行程编辑、账号、部署或预订支付。
- 后端依赖未锁定，离线 API 模拟需要 httpx；当前 requirements.txt 未将其列为独立测试依赖。模型 JSON 解析失败会在后端日志记录截断的原始输出，分享日志前应检查其中的旅行需求内容。

## 后续方向

v0.5.0 计划实现跨重启持久化、编辑与个人化，后续再推进系统评测。v0.4.0 的暂缓验收应在宣称完整验收前补齐；以实际代码与运行结果为准。

参考材料包括 [旅行规划参考项目](https://github.com/nameless0120/helloagents-trip-planner)。参考项目中的功能不等于本仓库已实现的能力。
