# Travel Agent Lab

一个使用 Python 自主实现的旅行 ReAct Agent：查询城市当前天气，再结合天气搜索景点建议。支持连续对话和 SQLite 长期记忆，明确的记忆命令直接操作数据库，旅行任务由 Agent 执行。

当前阶段为 **v0.2.0：多轮对话与本地长期记忆**。版本号是学习阶段编号，Git 标签和 Release 单独管理。

阶段记录：[v0.2.0](docs/version-0.2.0.md) · [v0.1.0](docs/version-0.1.0.md)。

## 当前能力

- 文本 ReAct 循环：模型输出 Action，Python 解析并执行工具，将 Observation 回传模型。
- 天气查询：wttr.in；景点搜索：Tavily。
- 函数和工具对象注册，函数签名绑定检查，执行耗时和结果记录。
- 结构化 Message、Agent 抽象基类、独立的 AgentConfig 与 LLMConfig。
- OpenAI 兼容模型客户端、模型调用异常处理、工具请求超时。
- 连续对话，按完整轮次裁剪旧历史；模型调用失败或步数耗尽时恢复本轮开始前的历史。
- SQLite 记忆新增、读取、字面关键词搜索、更新、删除和最近记录列表。
- 直接记忆命令不调用模型；MemoryTool 为 Agent 提供同一套存储能力。

当前为本地单用户命令行原型。对话历史只存在内存中，长期记忆保存在 `data/memory.db`，该目录已被 Git 忽略。尚无语义检索、RAG、LangChain、Web 界面或完整行程规划。多 provider 配置表示地址和密钥解析能力，不代表已逐一验证所有服务。

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
```

DeepSeek 专用密钥为空时，配置会回退读取 `OPENAI_API_KEY`。显式设置的 `OPENAI_BASE_URL` 优先于 provider 默认地址，切换服务商时应同步调整。`.env` 已加入忽略规则，不要提交真实凭证。

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
| `/new` | 清空对话历史，保留长期记忆 |
| `/quit` | 退出程序 |

部分明确的自然语言列表请求，例如“我保存的长期记忆是什么？”，也会直接查询数据库。这是固定表达匹配，不是通用意图识别。未知斜杠命令返回帮助，不进入 Agent。

记忆命令不调用模型；普通旅行请求进入 ReAct，可能调用模型和外部服务并产生费用。程序启动仍会初始化模型客户端，因此当前仍需可用的模型配置。模型客户端初始化不等于发起模型请求。

历史消息默认软上限为 20 条，可通过 `AGENT_MAX_HISTORY_MESSAGES` 调整。超限时删除最早的完整轮次，但保留当前轮次，因此不是严格的消息或 token 上限。

## 代码结构

```text
main.py                    组装配置、客户端、工具和 Agent
commands/memory_commands.py 直接记忆命令及固定表达分流
memory/item.py             MemoryItem 记忆数据结构
memory/sqlite_store.py     SQLite 存储、检索与维护
agents/base.py             公共接口与历史管理
agents/react_agent.py      ReAct 循环与文本 Action 解析
core/config.py             AgentConfig、LLMConfig 与环境变量解析
core/message.py            消息数据结构
core/llm_client.py         消息转换与模型请求
core/exceptions.py         LLMError
tools/base.py              工具抽象基类
tools/registry.py          注册、签名检查、描述、执行记录
tools/weather_tool.py      天气函数及 WeatherTool 包装类
tools/attraction_tool.py   景点搜索函数
tools/memory_tool.py       供 Agent 调用的记忆工具
prompts/system_prompt.md   含工具占位符的提示词模板
```

## 如何验证

语法检查不会发起外部请求：

```powershell
python -m compileall -q agents core tools memory commands main.py
```

已用临时数据库和模拟模型进行离线验证，覆盖记忆增删改查、重新连接后读取、完整轮次裁剪、失败历史恢复，以及直接命令跳过模型。学习过程中用户报告真实模型保存和重启后检索通过；收尾未重新调用付费模型或外部服务。当前没有纳入仓库的正式自动化测试套件、量化成功率或延迟基准。

## 当前限制

- 关键词搜索是字面包含匹配，英文区分大小写，不理解同义表达；列表按创建时间排序，更新不改变创建时间。
- 记忆不会自动注入每次请求。普通旅行任务是否检索记忆由模型结合提示词决定。
- 直接记忆命令不写入对话历史；更新或删除数据库不会同步清除历史中的旧信息。需要排除旧上下文时使用 `/new`。
- 失败历史恢复仅覆盖 `LLMError` 和步数耗尽，不撤销数据库写入、工具请求、执行记录或费用。
- 模型对记忆工具的写入行为依赖提示词，尚无独立的授权校验；执行记录中的 success 表示函数执行未抛异常，不保证业务成功。
- 无多用户隔离、自动总结或 TTL 遗忘；依赖未锁版本，`Ctrl+C` 和输入结束的退出处理暂缓完善。

## 后续方向

下一阶段可结合教材继续研究记忆检索、RAG、上下文工程、MCP、Agent 评估及 LangChain 对照实现。具体目标与顺序待讨论。其他 Agent 范式、向量数据库、知识图谱和多模态记忆不属于本版的必需功能。

参考材料包括 [旅行规划参考项目](https://github.com/nameless0120/helloagents-trip-planner)。参考项目中的功能不等于本仓库已实现的能力。
