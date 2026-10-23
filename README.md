# Travel Agent Lab

一个使用 Python 自主实现的旅行 ReAct Agent：查询城市当前天气，再结合天气搜索景点建议。项目用于逐步实践工具调用、消息管理、配置和 Agent 工程化，后续计划扩展 Memory、RAG、上下文工程、MCP、评估及 LangChain 对照实现。

当前阶段为 **v0.1.0 文档基线**。

## 当前能力

- 文本 ReAct 循环：模型输出 Action，Python 解析并执行工具，将 Observation 回传模型。
- 天气查询：wttr.in；景点搜索：Tavily。
- 函数和工具对象注册，函数签名绑定检查，执行耗时和结果记录。
- 结构化 Message、Agent 抽象基类、独立的 AgentConfig 与 LLMConfig。
- OpenAI 兼容模型客户端、模型调用异常处理、工具请求超时。

目前为单次任务命令行示例。每次 `run()` 会清空消息历史；没有跨轮记忆、RAG、LangChain、Web 界面或完整行程规划。多 provider 配置表示地址和密钥解析能力，不代表已逐一验证所有服务。

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
TAVILY_API_KEY=填写自己的密钥
```

DeepSeek 专用密钥为空时，配置会回退读取 `OPENAI_API_KEY`。显式设置的 `OPENAI_BASE_URL` 优先于 provider 默认地址，切换服务商时应同步调整。`.env` 已加入忽略规则，不要提交真实凭证。

```powershell
python main.py
```

当前问题写在 `main.py` 的 `question` 中，可以自行修改。正常示例流程为天气查询、景点搜索、最终回答；实际步骤由模型决定，网络错误和输出格式可能使任务提前结束或达到步数上限。

## 代码结构

```text
main.py                    组装配置、客户端、工具和 Agent
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
prompts/system_prompt.md   含工具占位符的提示词模板
```

## 如何验证

语法检查不会发起外部请求：

```powershell
python -m compileall -q agents core tools main.py
```

`python main.py` 为联网人工验证，会调用模型和搜索服务，可能产生服务费用。当前没有自动化测试套件、量化成功率或延迟基准。

## 后续方向

计划逐步加入 Memory / RAG、上下文工程、MCP、Agent 评估及 LangChain 对照实现。具体功能和顺序待下一阶段讨论。其他 Agent 范式暂缓，不作为当前旅行助手的必需功能。

参考材料包括 [旅行规划参考项目](https://github.com/nameless0120/helloagents-trip-planner)。参考项目中的功能不等于本仓库已实现的能力。
