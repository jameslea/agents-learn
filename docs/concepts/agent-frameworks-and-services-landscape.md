# Agent 框架与服务选型地图：现成能力如何服务 Runtime 实践

> 更新时间：2026-05-15
>
> 本文用于完整保存“现成可用的 Agent 框架与服务”探索结果。它不是某个框架的教程，而是面向后续项目 E / Agent Runtime 实验的选型地图：哪些能力可以直接借用，哪些能力适合参考思想，哪些能力不适合作为当前学习项目的主线依赖。

## 目录

- [文档定位](#文档定位)
- [一、总体判断](#一总体判断)
- [二、完整选型地图](#二完整选型地图)
- [三、Agent 编排与 Runtime 框架](#三agent-编排与-runtime-框架)
- [四、低代码与可视化 Agent 平台](#四低代码与可视化-agent-平台)
- [五、云厂商托管 Agent 服务](#五云厂商托管-agent-服务)
- [六、Trace、Observability 与 Evaluation](#六traceobservability-与-evaluation)
- [七、Guardrails、安全与红队测试](#七guardrails安全与红队测试)
- [八、Durable Execution、Human-in-the-loop 与工具协议](#八durable-executionhuman-in-the-loop-与工具协议)
- [九、对项目 E / Runtime 项目的启发](#九对项目-e--runtime-项目的启发)
- [十、建议的实践路线](#十建议的实践路线)
- [十一、选型原则与风险提示](#十一选型原则与风险提示)
- [参考资料](#参考资料)

## 文档定位

本文和 `agent-runtime-philosophy.md` 互补：

- `agent-runtime-philosophy.md` 讨论“Agent 开发为什么要走向 runtime/governance”。
- 本文讨论“如果要做 runtime/governance 实践，市面上有哪些框架、平台、服务可以直接参考或接入”。

本文也和 `agent-design-methodology.md` 互补：

- `agent-design-methodology.md` 更偏单个 Agent 系统如何设计。
- 本文更偏工具生态、工程选型和项目 E 的实践边界。

当前结论不是“选择一个最强框架”，而是：把现成生态拆成几类能力，分别评估它们能否帮助我们沉淀 Agent Runtime 经验。

## 一、总体判断

现成 Agent 生态已经很多，但它们解决的问题不一样。把它们混在一起比较，容易陷入“哪个框架更强”的误区。更合理的划分是：

| 类别 | 解决的问题 | 典型代表 |
|------|------------|----------|
| Agent 编排 / Runtime 框架 | 如何组织状态、工具调用、循环、分支、交接和多 Agent 协作 | LangGraph、OpenAI Agents SDK、Google ADK、Microsoft Agent Framework、AutoGen、CrewAI、LlamaIndex AgentWorkflow、Pydantic AI |
| 低代码 / 可视化平台 | 如何快速搭建可运行的 Agent 应用和 workflow | Dify、Coze / Coze Studio |
| 云厂商托管 Agent 服务 | 如何把 Agent 放进云平台的权限、数据、部署、监控和企业合规体系 | Amazon Bedrock Agents、Microsoft Foundry Agent Service、Microsoft Copilot Studio、Google Vertex AI Agent Engine |
| Trace / Observability / Evaluation | 如何记录、复盘、评估、对比和优化 Agent 行为 | Langfuse、Arize Phoenix、Braintrust、LangSmith |
| Guardrails / 安全 / 红队测试 | 如何限制输入、输出、工具调用、越权行为和攻击面 | NeMo Guardrails、Guardrails AI、Lakera Guard、Promptfoo |
| Durable Execution / HITL / 协议 | 如何支持长任务、恢复、人工审批和工具互操作 | Temporal、HumanLayer、LangGraph checkpoint/interrupt、MCP、Claude Code Skills |

对当前项目最重要的判断：

1. 不应把项目 E 变成“试用所有框架”的横向评测项目。这样会很快失焦。
2. 应该把项目 E 定位为“Agent Runtime & Governance 的最小实践项目”。
3. 现成框架应该作为参照和局部依赖，而不是替代我们的核心学习目标。
4. 最有价值的主线是：明确状态、结构化产物、trace、guardrails、eval、human-in-the-loop、成本延迟控制和版本治理。
5. 对学习项目而言，优先选择能暴露 runtime 本质的工具，而不是把复杂度封装得过深的平台。

一句话建议：

```text
项目 E 的主线可以用 LangGraph + Langfuse/Phoenix + 本地 Guardrails 作为最小组合，
用 Dify/Coze 和云厂商服务作为对照研究，
不要一开始就把项目做成通用平台或全量生产系统。
```

## 二、完整选型地图

### 2.1 Agent 编排 / Runtime 框架

| 框架 / SDK | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|------------|----------|----------------|------------------|----------|
| LangGraph | 状态机式 Agent 编排框架 | 显式 state、节点、边、checkpoint、interrupt、durable execution | 最适合作为项目 E 的主线对照框架 | 设计成本高于简单 SDK，需要先想清楚状态模型 |
| OpenAI Agents SDK | 轻量 Agent SDK | agent、handoff、guardrails、tracing、tools | 适合学习现代 Agent SDK 的最小抽象 | 生态和模型绑定度较高，跨 provider 需要额外适配 |
| Google ADK | 代码优先的 Agent 开发、调试、部署框架 | agent 定义、工具、部署到 Agent Engine / Cloud Run | 适合观察“本地开发到托管运行时”的路径 | Google 云生态绑定较强，学习成本不低 |
| Microsoft Agent Framework | AutoGen 与 Semantic Kernel 后继方向 | workflow、multi-agent、状态、telemetry、企业集成 | 适合观察企业级 Agent runtime 的设计趋势 | 当前仍处于预览或快速演进阶段，API 稳定性需要关注 |
| AutoGen | 多 Agent 对话与 AgentChat | 多 Agent 会话、角色交互、工具调用 | 适合作为多角色和会话式协作的反面/正面对照 | 容易把系统写成 prompt 接龙，工程边界需要额外治理 |
| CrewAI | 角色、任务、Crew、Flow | 角色建模、任务分配、流程化协作 | 适合学习“角色驱动协作”和 Flow 组合 | role/backstory 容易带来表演式复杂度 |
| LlamaIndex AgentWorkflow | 数据/RAG 生态中的 agentic workflow | RAG 工具化、FunctionAgent、AgentWorkflow、多 Agent | 适合项目 A / RAG 型 Agent 的延伸 | 如果不用 LlamaIndex 数据栈，通用 runtime 价值相对有限 |
| Pydantic AI | 面向 Python 的类型化 Agent 框架 | typed output、依赖注入、工具和结构化结果 | 适合做 schema-first、artifact-first 的小型 Agent | 编排和复杂 runtime 能力不如 LangGraph 直观 |

### 2.2 低代码与可视化 Agent 平台

| 平台 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|------|----------|----------------|------------------|----------|
| Dify | 开源 LLM 应用与 Agentic Workflow 平台 | workflow、RAG、agent、model management、观测能力 | 适合观察“产品化 Agent 应用”如何组织节点和配置 | 平台抽象较厚，容易跳过底层 runtime 思考 |
| Coze / Coze Studio | 可视化 Agent 开发平台和开源版本 | workflow、插件、知识库、发布渠道 | 适合作为低代码平台和业务交付形态参考 | 对本地代码级 runtime 实践帮助有限 |

### 2.3 云厂商托管 Agent 服务

| 服务 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|------|----------|----------------|------------------|----------|
| Amazon Bedrock Agents | AWS 上的托管 Agent 服务 | action groups、knowledge bases、prompt orchestration、云权限整合 | 适合研究企业云上 Agent 如何接入工具和数据 | 强依赖 AWS 生态，调试体验和成本需要评估 |
| Microsoft Foundry Agent Service | Azure / Microsoft Foundry 中的托管 Agent 服务 | 自动编排和托管、企业数据源、Azure AI Search、Cosmos DB 状态 | 适合研究企业级状态、合规和托管运行时 | Azure 绑定强，不适合作为本学习项目第一主线 |
| Microsoft Copilot Studio | 面向业务用户的可视化 Agent 构建平台 | 业务流程、连接器、知识、actions、发布治理 | 适合研究企业内 Agent 交付和权限治理 | 更偏业务平台，不适合用来学习底层机制 |
| Google Vertex AI Agent Engine / ADK Deploy | Google Cloud 上的 Agent 托管和扩展运行环境 | ADK 本地开发到 Agent Engine / Cloud Run 部署 | 适合研究“代码框架 + 云 runtime”的组合 | 云生态绑定强，初期会引入很多非核心复杂度 |

国内也已经出现一批类似服务。它们通常不完全等同于 AWS Bedrock Agents / Microsoft Foundry Agent Service / Google Agent Engine 这类“云上 Agent runtime”，而是更常见地表现为：

```text
大模型 MaaS + 低代码 Agent 应用构建 + RAG 知识库 + 插件/工具 + 发布渠道 + 评测/观测
```

| 国内平台 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|----------|----------|----------------|------------------|----------|
| 阿里云百炼 Model Studio | 通义千问生态下的大模型应用开发平台 | 智能体应用、RAG 知识库、插件、MCP、API 调用、发布、版本管理、长期记忆 | 很适合作为国内云上 Agent 应用平台参照 | 与阿里云模型、RAM 权限、百炼控制台绑定较强 |
| 百度千帆 Agent 开发平台 / AppBuilder | 企业级大模型应用开发管理平台 | RAG、Agent、工作流、UI Builder、官方组件、MCP 服务、OpenAPI、SDK、团队协作 | 适合研究国内企业级 Agent 平台的完整工具链 | 平台能力较厚，底层 runtime 细节不一定透明 |
| 腾讯云智能体开发平台 ADP | 腾讯云上的智能体构建平台 | LLM+RAG、Workflow、Multi-agent、知识库、插件广场、模型广场、提示词模板、HTTP/SSE/WebSocket 调用 | 适合作为“工作流 + 多智能体 + 云接口发布”的国内样本 | 生态绑定腾讯云和腾讯系应用集成 |
| 华为云 AgentArts | 企业级一站式智能体构建与运营平台 | 单智能体、工作流、多智能体、Skill、MCP、插件、知识库、运行时、全链路观测和评估、安全保障 | 在“企业级 runtime/governance”方向最值得关注 | 产品较新，公测与区域可用性、API 稳定性需要核查 |
| 火山引擎扣子 / Coze | Agent 可视化开发平台与开源生态 | Coze Studio、Workflow、Plugin、创建/调试/部署/版本管理；Coze Loop 覆盖 prompt、评测、Agent 轨迹和全链路观测 | 非常适合研究低代码 Agent 平台和 AgentOps 思路 | 更偏平台化和低代码，直接学习底层 runtime 需要拆解 |
| 科大讯飞星辰 Agent | 星火生态下的 Agent 开发平台 | 指令型/工作流/自主 Agent、RAG、工具、评测、微调、多模型兼容、API/MCP/飞书等发布渠道 | 适合作为国内大模型公司 Agent 平台参考 | 严格说不是传统云厂商托管服务 |
| 京东云 JoyAgent / JDGenie | 京东开源的端到端产品级多智能体系统 | 多 Agent 产品形态、DAG 执行、子智能体和工具可插拔、报告/PPT/文件交付 | 适合研究“开箱即用产品级 Agent”的系统设计 | 更偏开源产品/框架，不完全是托管云服务 |

### 2.4 Trace、Observability 与 Evaluation

| 工具 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|------|----------|----------------|------------------|----------|
| Langfuse | LLM application observability、prompt management、evaluation | trace、session、cost、latency、LLM-as-judge、annotation queue | 非常适合作为项目 E 观测层候选 | 自托管和数据治理需要额外配置 |
| Arize Phoenix | 开源 AI observability 与 evaluation | OpenTelemetry trace、RAG 分析、evals、framework integrations | 适合本地优先的 trace/eval 实验 | 产品线和概念较多，需要控制接入范围 |
| Braintrust | eval、prompt playground、dataset、remote evals | 数据集、实验对比、scorer、agent eval | 适合研究评估平台和回归集管理 | 更偏平台化，学习项目不宜过早重度依赖 |
| LangSmith | LangChain/LangGraph 生态下的 observability/eval | tracing、dataset、experiments、debugging | 如果项目 E 主线使用 LangGraph，天然适配 | 与 LangChain 生态绑定度更高 |

### 2.5 Guardrails、安全与红队测试

| 工具 / 服务 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|-------------|----------|----------------|------------------|----------|
| NeMo Guardrails | 面向 LLM 应用的可编程护栏工具包 | 输入/输出 rails、对话行为约束、可编程策略 | 适合研究 guardrails 作为独立层的设计方式 | 配置和运行方式可能偏重，对小项目需要裁剪 |
| Guardrails AI | 输出校验和 Guard 执行引擎 | Pydantic/schema validation、validated output、失败反馈 | 适合 artifact/schema-first 的输出治理 | 对复杂工具权限和运行时安全覆盖有限 |
| Lakera Guard | 商业化 LLM 安全 API | prompt injection、jailbreak、内容威胁检测 | 适合作为外部安全检测服务参考 | API 调用增加成本和延迟，外部依赖明显 |
| Promptfoo | LLM eval 与 red teaming 工具 | prompt 测试、CI、agent red team、RAG red team | 很适合项目 E 做“攻击样本 + 回归测试” | 红队测试需要设计高质量场景，否则容易形式化 |

### 2.6 Durable Execution、Human-in-the-loop 与工具协议

| 工具 / 协议 | 核心定位 | 适合借鉴的能力 | 对当前项目的价值 | 主要风险 |
|-------------|----------|----------------|------------------|----------|
| Temporal | Durable execution / workflow engine | 长任务、重试、恢复、信号、活动编排 | 适合研究长任务和可靠执行的底层模型 | 对当前学习项目偏重，建议先只借鉴思想 |
| HumanLayer | Agent 的人工审批和决策层 | human approval、决策请求、边界接管 | 适合研究 HITL 如何产品化 | 作为外部服务会引入额外依赖 |
| LangGraph checkpoint / interrupt | LangGraph 内建持久化和人工介入能力 | checkpoint、resume、interrupt before/after | 和项目 E 主线高度相关 | 需要先把状态和恢复点设计清楚 |
| MCP | Model Context Protocol，工具与数据源标准协议 | 工具发现、资源访问、外部系统连接 | 适合项目 E 的工具协议和权限治理参考 | MCP server 自身也会引入供应链和权限风险 |
| Claude Code Skills | 文件系统式技能封装 | `SKILL.md`、脚本、资源、触发描述、版本说明 | 非常适合“Skills + Guardrails”方法论研究 | 技能触发仍依赖模型判断，需要评估和版本治理 |

## 三、Agent 编排与 Runtime 框架

### 3.1 LangGraph

LangGraph 是当前最值得深入研究的主线框架之一。它的价值不在于“让 Agent 更聪明”，而在于把 Agent 的执行过程显式化：

- 用 state 保存任务状态。
- 用 node 表达步骤。
- 用 edge 表达转移。
- 用 conditional edge 表达分支。
- 用 checkpoint 支持持久化和恢复。
- 用 interrupt 支持人工介入。
- 用 durable execution 支持长任务和故障恢复。

这与我们从 A-D-lite 得到的经验高度一致：Agent 的复杂度最终都会落到状态、恢复、终止、验证和 trace 上。

对项目 E 的启发：

- 项目 E 可以不直接追求“通用 Agent 框架”，而是先实现一个最小 runtime，然后用 LangGraph 作为对照。
- 如果自己写状态机，会更理解 runtime 本质；如果接入 LangGraph，会更快进入 checkpoint、interrupt 和可观测性。
- 最合理的方式不是二选一，而是：核心概念自己实现最小版，工程化能力参考 LangGraph。

建议实践：

| 实践项 | 是否推荐 |
|--------|----------|
| 用 LangGraph 实现一个最小 agent loop | 推荐 |
| 用 LangGraph checkpoint 做断点续跑 | 推荐 |
| 用 interrupt 实现人工审批点 | 推荐 |
| 一开始就做复杂多 Agent 图 | 不推荐 |
| 一开始就封装通用 graph framework | 不推荐 |

### 3.2 OpenAI Agents SDK

OpenAI Agents SDK 的抽象很清晰，核心包括：

- Agent。
- Tools。
- Handoffs。
- Guardrails。
- Tracing。
- Sessions / conversation state。

这说明现代 Agent SDK 已经把 guardrails 和 tracing 放到了基础能力层，而不是业务代码之外的附加项。

对项目 E 的启发：

- 可以参考它的抽象命名：agent、tool、handoff、guardrail、trace。
- 可以研究它如何把 guardrail 做成输入/输出检查，而不只是 prompt 约束。
- 可以把它作为“轻量 SDK 风格”的对照，而 LangGraph 作为“状态机 runtime 风格”的对照。

建议实践：

| 实践项 | 是否推荐 |
|--------|----------|
| 阅读其 guardrails / tracing 抽象 | 推荐 |
| 用一个小例子对照 LangGraph | 推荐 |
| 把项目 E 绑定到 OpenAI SDK | 暂不推荐 |
| 在多 provider 环境下直接作为统一抽象层 | 谨慎 |

### 3.3 Google ADK

Google Agent Development Kit 的定位更接近“从本地开发、调试到云端部署”的完整工具链。它强调：

- 代码优先开发。
- Agent 调试。
- 工具与模型集成。
- 可部署到 Google Cloud 的 Agent Engine 或 Cloud Run。
- 与 Google 生态结合。

对项目 E 的启发：

- ADK 展示了“Agent framework + managed runtime”的路径。
- 它把部署和运行环境作为重要部分，而不是只停留在本地 agent loop。
- 它适合研究“Agent 应用如何从本地代码走向托管运行”。

但对当前学习项目来说，ADK 不宜作为第一主线。原因是云端部署、认证、环境和服务配置会引入很多非核心复杂度。

### 3.4 Microsoft Agent Framework

Microsoft Agent Framework 是值得关注的新方向。它被定位为 AutoGen 和 Semantic Kernel 的后继整合方向，强调：

- 单 Agent 与多 Agent 抽象。
- workflow。
- 状态管理。
- 类型安全。
- filters。
- telemetry。
- 长任务与 human-in-the-loop 场景。
- 与 Microsoft / Azure 生态集成。

这和我们讨论的 Agent Runtime 思路非常接近：Agent 不只是模型调用，而是一套可部署、可观测、可治理的运行系统。

对项目 E 的启发：

- 它说明企业级 Agent 框架正在从“多 Agent 会话”走向“workflow + state + telemetry + governance”。
- 它可以作为“企业级 runtime 设计”的重要参照。
- 但它仍处于快速演进阶段，学习项目不应过早重度依赖。

建议实践：

| 实践项 | 是否推荐 |
|--------|----------|
| 跟踪其 workflow/state/telemetry 设计 | 推荐 |
| 与 LangGraph 做概念对照 | 推荐 |
| 用它重写项目 E 主线 | 暂不推荐 |

### 3.5 AutoGen

AutoGen 的价值在于它较早把多 Agent 会话、角色交互和工具调用变成了可编程框架。它适合探索：

- 多 Agent conversation。
- assistant/user proxy。
- group chat。
- agent handoff。
- 会话式修复。

但项目 B 的经验已经说明：多 Agent 不会自然产生高质量。多个 Agent 如果没有结构化产物、状态边界、评价标准和终止条件，很容易变成高成本 prompt 接龙。

对项目 E 的启发：

- AutoGen 适合作为“多角色会话范式”的对照。
- 项目 E 应关注如何把多 Agent 的交接变成 artifact，而不是只保留聊天记录。
- 多 Agent 框架必须配合 trace、eval 和 human review。

### 3.6 CrewAI

CrewAI 的优点是角色、任务、团队协作概念直观。它对学习者友好，容易把现实组织中的角色映射到 Agent：

- Role。
- Goal。
- Backstory。
- Task。
- Crew。
- Flow。

CrewAI Flows 也体现出一个趋势：即使是角色驱动框架，也需要更可控的流程编排层。

对项目 E 的启发：

- 角色是认知组织方式，不等于运行时边界。
- 角色之间的交接必须通过结构化 artifact。
- Backstory 可以提升表达一致性，但不能替代工具权限、安全策略和评估。

### 3.7 LlamaIndex AgentWorkflow

LlamaIndex 的强项在数据、索引、RAG 和知识工作流。AgentWorkflow 的价值在于：

- 把 RAG pipeline 和 tools 纳入 Agent。
- 提供 FunctionAgent、AgentWorkflow 等预置能力。
- 支持多 Agent / agentic workflow。

对项目 A 很有价值，对项目 E 的通用 runtime 价值则相对间接。

建议：

- 如果项目 E 关注 RAG Agent 的观测和评估，可以使用 LlamaIndex。
- 如果项目 E 关注通用 runtime，不应一开始绑定 LlamaIndex。

### 3.8 Pydantic AI

Pydantic AI 的最大价值是把 Agent 开发拉回 Python 工程习惯：

- 类型化输入输出。
- structured output。
- dependency injection。
- tool definitions。
- schema-first 开发。

这与我们强调的 artifact protocol 非常契合。它适合写小而稳的 Agent，而不是复杂自治系统。

对项目 E 的启发：

- schema 是 Agent 工程化的基础，不是可选项。
- 结构化产物应成为节点之间的默认交接方式。
- 小型 Agent 可以优先用 typed output，而不是长文本约定。

## 四、低代码与可视化 Agent 平台

### 4.1 Dify

Dify 的价值在于它把很多 LLM 应用常见能力产品化：

- Chatbot。
- Agent。
- Workflow。
- RAG pipeline。
- model management。
- observability。
- deployment。

对于学习项目，Dify 最适合作为“产品化形态参考”：

- 看它如何定义节点。
- 看它如何配置工具。
- 看它如何管理模型。
- 看它如何组织 workflow。
- 看它如何暴露调试信息。

但不建议把项目 E 直接做成 Dify 插件或 Dify 应用。原因是平台已经封装了很多细节，会降低我们对 runtime 本质的学习收益。

### 4.2 Coze / Coze Studio

Coze 和 Coze Studio 适合观察可视化 Agent 平台如何面向业务用户：

- 知识库。
- workflow。
- 插件。
- 多渠道发布。
- 可视化调试。

它对我们最大的价值不是代码复用，而是产品视角：

- 业务用户需要什么样的配置界面。
- Agent 工具如何被包装成可选择能力。
- workflow 节点如何对非工程用户表达。
- 发布、权限和版本如何呈现。

对项目 E：

- 可以做对照研究。
- 不建议作为主线依赖。
- 可以借鉴“工具目录”“技能目录”“workflow 可视化”的概念。

## 五、云厂商托管 Agent 服务

云厂商托管 Agent 服务解决的是另一个层面的问题：企业如何把 Agent 放进已有云资源、身份、权限、数据、监控和合规体系。

这些服务不是学习 runtime 的最佳起点，但非常适合帮助我们理解生产环境会遇到什么。

### 5.1 Amazon Bedrock Agents

Bedrock Agents 的典型价值：

- 接入 foundation models。
- 配置 action groups。
- 接入 knowledge bases。
- 管理 agent versions / aliases。
- 与 AWS 权限、API、数据服务结合。

对项目 E 的启发：

- 工具调用在云上通常会被包装成 action group。
- Agent 版本和 alias 是生产治理的重要概念。
- 知识库、工具和模型需要一起纳入版本管理。

### 5.2 Microsoft Foundry Agent Service

Microsoft Foundry Agent Service 的价值在企业集成：

- Agent orchestration and hosting。
- 使用 Azure AI Search、SharePoint、Bing、Logic Apps、Azure Functions、OpenAPI 等企业工具。
- 可以使用自有 Azure resources，例如存储、搜索、Cosmos DB 会话状态。
- 更强调企业合规、权限和治理。

对项目 E 的启发：

- 状态存储可能不是一个本地文件，而是企业级存储。
- 工具权限和数据边界需要进入平台级治理。
- Agent runtime 与云身份和资源权限密切相关。

### 5.3 Microsoft Copilot Studio

Copilot Studio 更偏业务平台：

- 用自然语言或可视化方式创建 Agent。
- 接入 Microsoft 365、Power Platform 和业务连接器。
- 支持知识、actions、发布和分析。

对项目 E 的启发：

- 最终用户需要的是可治理的业务 Agent，而不是框架 API。
- 企业 Agent 往往要解决“谁能创建、谁能发布、谁能调用、谁能审批”的问题。
- 但它不是当前学习项目的底层实现候选。

### 5.4 Google Vertex AI Agent Engine / ADK Deploy

Google 的路径是：

```text
ADK 本地开发 -> 调试 -> 部署到 Cloud Run 或 Agent Engine -> 云端运行和扩展
```

对项目 E 的启发：

- 一个成熟 Agent 需要从本地开发环境迁移到可托管运行环境。
- 部署本身也是 runtime 的一部分。
- 但在学习阶段，云端托管容易把注意力从 state、trace、eval、guardrails 转移到云配置。

### 5.5 国内云厂商与大模型平台的类似服务

国内平台的方向已经很清晰：主流云厂商和大模型平台都在把“模型调用”升级为“Agent 应用开发与运行平台”。它们和海外云厂商托管 Agent 服务的相同点是：

- 都提供模型选择和调用。
- 都提供 RAG / 知识库。
- 都提供插件、工具或组件生态。
- 都支持工作流或多智能体编排。
- 都提供 API 调用、网页、企业应用或第三方渠道发布。
- 都开始强调评测、观测、版本管理和安全治理。

不同点也很明显：

- 国内平台更偏“低代码应用开发平台”，而不是先暴露底层 runtime API。
- 很多能力围绕具体生态展开，例如阿里云 RAM / 百炼、百度 AI 搜索与千帆组件、腾讯云与企微/小程序生态、华为云 MaaS 与企业安全、火山引擎扣子生态。
- “工具权限、可回放 trace、durable execution、human-in-the-loop、版本治理”这些 runtime 能力有的平台已经提供入口，但抽象方式未必统一。
- 如果作为学习项目依赖，很容易被平台 UI 和云资源配置牵引，反而看不清 runtime 的本质。

#### 阿里云百炼 Model Studio

阿里云百炼的智能体应用支持用零代码方式把大模型与外部工具、知识库连接起来。官方文档强调智能体会根据用户意图规划任务并自主调用外部工具。核心能力包括：

- 知识库 RAG。
- 官方插件和自定义插件。
- API 调用。
- 第三方平台发布。
- 组件集成。
- 版本管理和回滚。
- MCP 相关计费说明。
- 长期记忆。

对项目 E 的启发：

- 版本管理和发布渠道应该进入 runtime governance 范围。
- MCP、插件、知识库和长期记忆都会影响成本和上下文，应纳入 trace。
- Agent 应用发布后，配置变更需要可追踪、可回滚。

#### 百度千帆 Agent 开发平台 / AppBuilder

百度千帆 Agent 开发平台定位为企业级大模型应用开发管理平台，提供 RAG、Agent、工作流、UI Builder 等工具链，同时提供官方组件、创建组件、应用分发、MCP 服务、知识库管理、数据库管理、Prompt 模板管理、批量任务、团队协作、OpenAPI 和 SDK。

对项目 E 的启发：

- Agent 平台最终会走向“应用开发管理平台”，不只是一个 agent loop。
- 组件、知识库、Prompt 模板、团队协作、OpenAPI / SDK 都是平台化后必须治理的对象。
- 项目 E 不必实现这些完整能力，但可以先定义 metadata 和 version 字段，为后续扩展留边界。

#### 腾讯云智能体开发平台 ADP

腾讯云 ADP 明确提供 LLM+RAG、Workflow、Multi-agent 等智能体开发框架，并包含知识库、工作流、Multi-Agent、插件广场、模型广场、提示词模板，以及 WebSocket、HTTP SSE、文件对话等接口文档。

对项目 E 的启发：

- 国内平台已经把 Workflow 和 Multi-agent 作为并列模式，而不是只强调单 Agent。
- 对话接口、文件上传、离线文档和 COS 这类集成能力说明：Agent runtime 很快会和文件、对象存储、企业知识库绑定。
- 如果项目 E 做工具治理，文件类工具和文档上传类工具应作为高优先级样本。

#### 华为云 AgentArts

华为云 AgentArts 是目前国内描述上最接近“企业级 Agent runtime/governance”的平台之一。其产品页强调：

- 单智能体、工作流、多智能体协作。
- Skill、MCP、插件、知识库 RAG。
- 企业级 Agent 运行服务。
- 全链路应用观测。
- 日志、性能指标、异常检测与报警。
- 效果评估器。
- 安全保障。

对项目 E 的启发：

- Agent Runtime 的八层模型在企业平台中几乎都会出现：开发、运行、资产、数据、测试发布、运营监控、安全保障。
- 观测和评估不是后期增强，而是企业 Agent 平台的核心卖点。
- Skill 可以作为平台资产，而不是散落在项目中的 prompt 或脚本。

#### 火山引擎扣子 / Coze

扣子是国内非常典型的 Agent 平台样本。火山引擎开发者社区资料显示，Coze Studio 是一站式 AI Agent 可视化开发工具，核心包括 Workflow 引擎、Plugin 框架、创建、调试、部署和版本管理。Coze Loop 则聚焦 Agent 从开发到运维的全链路管理，覆盖 Prompt 开发、多维度评测、Agent 轨迹、Agent Tool 选择质量和全链路可观测性。

对项目 E 的启发：

- AgentOps 是独立方向，不应只做“业务 Agent”。
- Tool selection quality 是多步 Agent 很重要的评估指标。
- 低代码平台的核心价值不是“拖拽”，而是把 workflow、plugin、trace、eval、version 做成统一产品体验。

#### 科大讯飞星辰 Agent

讯飞星辰 Agent 虽然不是传统云厂商服务，但它是国内大模型平台中较完整的 Agent 开发平台。官方文档描述其支持：

- 指令型、工作流、自主 Agent。
- 场景模板和技术模板。
- 场景化 RAG。
- 工具。
- 效果测评、微调定制、闭环优化。
- 多源模型适配，包括讯飞星火、DeepSeek、Qwen、Stable Diffusion 等。
- 发布为个人智能体、星火 App、微信公众号、API、MCP Server、飞书机器人和虚拟人交互平台。

对项目 E 的启发：

- 发布渠道本身会影响权限、安全和 trace。
- MCP Server 正在成为国内 Agent 平台的重要发布形态。
- “效果测评 + 微调 + 闭环优化”说明 eval 不应只用于验收，也会反过来驱动模型和工具优化。

#### 京东云 JoyAgent / JDGenie

JoyAgent-JDGenie 更像“端到端开源多智能体产品”，不是严格意义上的托管 Agent 服务。它的价值在于产品完成度和多 Agent 系统设计：

- 前端、后端、框架、引擎和核心子智能体整体开源。
- 支持 report agent、search agent 等子智能体。
- 支持 plan and executor、ReAct 等模式。
- 支持高并发 DAG 执行。
- 支持 HTML、PPT、Markdown 等交付样式。
- 支持子 Agent 和工具可插拔。

对项目 E 的启发：

- 产品级 Agent 最终需要交付 artifact，而不仅是聊天回答。
- 多智能体系统需要 DAG、上下文管理和交付格式管理。
- 对学习项目来说，它更适合作为“产品级多 Agent 系统阅读对象”，不适合作为最小 runtime 主线。

#### 国内服务对项目 E 的总体启发

国内平台进一步验证了一个判断：

```text
Agent 平台竞争已经从“谁有模型 API”转向
“谁能提供完整的 Agent 应用开发、运行、观测、评估、发布和治理链路”。
```

因此，项目 E 的定位不应只是“评估与安全防线”，而应该更明确地沉淀为：

```text
Agent Runtime & Governance Lab
```

但实现边界仍要保持克制：

- 不做低代码 UI。
- 不做云厂商适配。
- 不做完整插件市场。
- 不做企业权限系统。
- 只抽象这些平台反复出现的共同能力：task、state、artifact、tool、skill、guardrail、trace、eval、approval、version。

建议把国内平台作为研究样本，而不是第一阶段依赖：

| 平台 | 项目 E 中的角色 |
|------|----------------|
| 阿里云百炼 | 研究 Agent 应用、插件、MCP、版本管理 |
| 百度千帆 | 研究企业级应用开发管理平台结构 |
| 腾讯云 ADP | 研究 Workflow / Multi-agent / 云接口发布 |
| 华为云 AgentArts | 研究企业级 runtime、观测、评估、安全 |
| 火山引擎 Coze | 研究低代码 AgentOps、workflow、plugin、trace、eval |
| 讯飞星辰 Agent | 研究多源模型、发布渠道、MCP Server |
| JoyAgent / JDGenie | 研究产品级多 Agent 和 artifact 交付 |

## 六、Trace、Observability 与 Evaluation

Agent 调试不能只看最终回答。需要记录：

- 用户输入。
- 系统 prompt。
- 中间状态。
- 工具调用。
- 工具参数。
- 工具返回。
- 错误。
- 重试。
- token。
- latency。
- cost。
- 最终产物。
- judge / evaluator 结果。
- 人工标注。

### 6.1 Langfuse

Langfuse 是非常适合项目 E 的候选工具。它覆盖：

- tracing。
- sessions。
- prompt management。
- evaluation。
- LLM-as-a-judge。
- annotation queue。
- cost / latency tracking。
- 常见框架集成。

对项目 E 的价值：

- 可以把 D-lite 的 JSONL trace 映射到 Langfuse trace。
- 可以跟踪 DeepSeek / MiniMax 等多 provider 调用耗时。
- 可以把人工评审结果写回 evaluation。
- 可以形成“改动前后对比”的实验闭环。

建议先做最小接入：

```text
run_id -> trace
attempt -> span
llm call -> generation
tool call -> span
verification -> score / event
final status -> trace metadata
```

### 6.2 Arize Phoenix

Phoenix 的价值在开源、本地、OpenTelemetry 和 evaluation：

- 支持 LLM traces。
- 支持 RAG analysis。
- 支持 evals。
- 可接收 OpenTelemetry traces。
- 与多个框架、模型 provider 和语言生态集成。

对项目 E 的价值：

- 如果希望更贴近 open telemetry / observability 思路，Phoenix 很适合。
- 它可以作为 Langfuse 的替代或对照。
- 对 RAG 项目 A 的评估也有价值。

### 6.3 Braintrust

Braintrust 更强调 evaluation workflow：

- dataset。
- experiment。
- scorer。
- playground。
- remote evals。
- prompt 对比。
- agent eval。

对项目 E 的价值：

- 帮助建立“回归集”思维。
- 适合把失败案例沉淀为可重复评估数据。
- 适合研究如何评价多步 Agent，而不是只评价一次模型输出。

但作为学习项目主线，Braintrust 可能偏平台化。建议作为后续增强项。

### 6.4 LangSmith

LangSmith 与 LangChain/LangGraph 生态结合紧密：

- trace。
- dataset。
- experiments。
- prompt / chain 调试。
- LangGraph 观测。

如果项目 E 主线选择 LangGraph，LangSmith 是自然候选。但为了避免生态绑定，也可以优先考虑 Langfuse 或 Phoenix。

### 6.5 对当前项目的建议

优先级建议：

| 优先级 | 工具 | 原因 |
|--------|------|------|
| 第一优先 | Langfuse 或 Phoenix | 更贴近 trace/eval/runtime 目标 |
| 第二优先 | LangSmith | 如果主线使用 LangGraph，可以作为自然补充 |
| 第三优先 | Braintrust | 更适合成熟 eval 平台和回归管理 |

最小目标不是接入最强平台，而是形成稳定数据模型：

```text
TraceEvent
TraceSpan
LLMCall
ToolCall
Artifact
EvaluationResult
HumanReview
```

只要本地数据模型稳定，后续可以导出到不同观测平台。

## 七、Guardrails、安全与红队测试

Guardrails 必须从 prompt 中独立出来。Prompt 可以表达意图，但不能提供可靠边界。

项目 E 至少要区分四类 guardrails：

| 类型 | 示例 | 实现方式 |
|------|------|----------|
| 输入护栏 | prompt injection、越权请求、敏感信息 | 分类器、规则、外部安全 API |
| 输出护栏 | JSON schema 不合法、引用缺失、格式错误 | schema validation、Pydantic、Guardrails AI |
| 工具护栏 | 禁止危险命令、限制文件范围、限制外部写操作 | allowlist、denylist、AST 检查、权限模型 |
| 运行时护栏 | timeout、max steps、budget、blocked 终态 | runtime policy、状态机、执行器 |

### 7.1 NeMo Guardrails

NeMo Guardrails 适合研究“可编程 rails”的思想：

- 输入 rails。
- 输出 rails。
- 对话行为约束。
- 与应用代码之间形成独立控制层。

它对项目 E 的启发是：guardrails 应该是系统结构的一部分，而不是散落在各个 prompt 里的提醒。

### 7.2 Guardrails AI

Guardrails AI 更适合 structured output 和 validation：

- Guard。
- Pydantic 对象。
- validated output。
- validation success / failure。

它和项目 E 的 artifact protocol 很契合。

可实践方向：

- 对 Agent 输出的 patch proposal 做 schema validation。
- 对研究报告的引用列表做结构校验。
- 对 tool call proposal 做参数校验。

### 7.3 Lakera Guard

Lakera Guard 是外部安全 API，更偏商业化防护：

- prompt injection。
- jailbreak。
- 恶意输入。
- 文档投毒风险。

它对项目 E 的价值是作为“外部安全服务”的参考，而不是必选依赖。

需要注意：

- 每次调用会增加延迟。
- 需要处理误报和漏报。
- 需要把结果纳入 runtime policy，而不是只记录日志。

### 7.4 Promptfoo

Promptfoo 对项目 E 很有价值，因为它适合做红队测试和回归测试：

- prompt eval。
- LLM red teaming。
- agent red teaming。
- RAG red teaming。
- CI/CD 集成。

项目 E 可以从 Promptfoo 学到：

- 安全不是只靠静态规则，也要靠攻击样本。
- 每次改 prompt、tool policy 或 runtime，都要跑回归。
- 红队样本应变成长期资产。

建议实践：

```text
构造 20 个攻击样本：
- 越权文件访问
- prompt injection
- 要求绕过安全检查
- 诱导执行危险命令
- 诱导泄露环境变量
- 诱导修改非目标文件
- 诱导忽略验证失败
```

然后把这些样本接入 eval runner，作为项目 E 的安全回归集。

## 八、Durable Execution、Human-in-the-loop 与工具协议

### 8.1 Temporal

Temporal 是 durable execution 的典型代表。它解决的问题包括：

- 长任务。
- 崩溃恢复。
- retry。
- timer。
- signals。
- workflow history。
- 活动编排。

Agent 长任务天然需要这些能力，但 Temporal 对当前学习项目偏重。

对项目 E 的建议：

- 暂时不直接接入 Temporal。
- 先借鉴它的思想：workflow history、activity、retry policy、signal、resume。
- 等项目 E 的本地 runtime 成型后，再考虑 Temporal adapter。

### 8.2 HumanLayer

HumanLayer 的价值是把 human-in-the-loop 明确产品化：

- Agent 到达边界时发起人工决策请求。
- 人类审批或拒绝。
- 决策结果回到 workflow。
- 可以设置 SLA、上下文和风险等级。

对项目 E 的启发：

- 人工介入不是“暂停问一下用户”这么简单。
- 它应该有结构化请求、上下文、审批结果和 trace。
- 人工审批本身也是 runtime event。

项目 E 可先实现本地最小模型：

```text
ApprovalRequest
ApprovalDecision
approval_required policy
needs_human final/intermediate status
```

### 8.3 MCP

MCP 的价值在于工具和数据源标准化。它使 Agent 可以通过统一协议连接外部工具、资源和服务。

对项目 E 的启发：

- 工具不应该只是 Python 函数列表。
- 工具应该有名称、描述、参数 schema、权限级别、风险等级和调用 trace。
- MCP server 可以作为工具生态接口，但需要权限治理。

MCP 同时带来新的风险：

- 第三方 server 可信度。
- 工具描述投毒。
- 权限过宽。
- 供应链风险。
- 数据外泄。

所以项目 E 不应简单地“支持 MCP 就完事”，而应研究：

```text
Tool Registry -> Permission Policy -> Runtime Approval -> Tool Call Trace
```

### 8.4 Claude Code Skills

Claude Code Skills 对我们的方法论启发很大。Skill 是一个可发现的能力包，通常包括：

- `SKILL.md`。
- 描述什么时候触发。
- 具体操作说明。
- 可选脚本。
- 可选模板或资源。
- 版本说明。

这和我们提出的“不要追求万能 Agent，而是构建 Skills + Guardrails”高度一致。

对项目 E 的启发：

- Skill 不只是函数，也不是 prompt 片段。
- Skill 是经验封装：触发条件、上下文选择、执行步骤、工具使用、输出要求、验证方式。
- Skill 需要版本治理和评估。
- Skill 应该能被 runtime 发现、选择、执行和追踪。

项目 E 可以实现一个很小的 skill registry：

```text
skills/
  error-classification/SKILL.md
  safe-patch-proposal/SKILL.md
  sandbox-verification/SKILL.md
  trace-review/SKILL.md
```

每个 Skill 至少包含：

| 字段 | 说明 |
|------|------|
| name | 技能名称 |
| description | 触发描述 |
| inputs | 输入契约 |
| outputs | 输出契约 |
| tools | 需要的工具 |
| guardrails | 调用前后必须执行的护栏 |
| examples | 正例和反例 |
| evals | 验证方式 |

## 九、对项目 E / Runtime 项目的启发

前面的生态梳理说明，项目 E 不应该只是“评估与安全防线”的附属横向模块。它已经可以重新定位为一个独立探索项目：

```text
Agent Runtime & Governance Lab
```

但这个独立项目也不能膨胀成产品级平台。它的价值应该是：

- 用最小代码复现 Agent runtime 的关键层。
- 对照主流框架和服务，理解它们为什么这样设计。
- 沉淀可复用方法论、数据结构和测试样本。
- 形成后续开发 Agent 时可以复用的工程骨架。

### 9.1 项目 E 的核心问题

项目 E 应回答这些问题：

| 问题 | 需要产出的东西 |
|------|----------------|
| Agent 的任务契约如何定义？ | TaskContract schema |
| 中间产物如何稳定交接？ | Artifact schema |
| 工具权限如何建模？ | ToolRegistry + PermissionPolicy |
| 每一步如何记录？ | TraceEvent / TraceSpan |
| 失败如何分类？ | ErrorType / FailureReason |
| 什么时候停止？ | StopPolicy / BudgetPolicy |
| 什么时候人工介入？ | ApprovalPolicy / ApprovalRequest |
| 如何评估改动是否更好？ | EvalDataset / EvalRunner / Score |
| 如何管理 prompt、tool、skill 版本？ | Version metadata |

### 9.2 项目 E 不应该做什么

为了避免复杂度失控，项目 E 明确不做：

- 不做通用低代码平台。
- 不做完整云托管服务。
- 不做插件市场。
- 不做全量 MCP 平台。
- 不做企业权限系统。
- 不做复杂 UI。
- 不做多租户。
- 不做大规模分布式执行。

这些能力可以研究，但不进入最小实现。

### 9.3 项目 E 应该做什么

项目 E 最值得做的是一个“最小但完整”的 runtime 骨架：

```text
TaskContract
  -> RuntimeState
  -> Skill / Agent Step
  -> Tool Governance
  -> Artifact
  -> Guardrail Check
  -> Trace
  -> Evaluation
  -> Human Approval if needed
  -> Final Status
```

最小闭环可以复用 D-lite 的场景：

```text
损坏脚本 -> 错误分类 -> 修复建议 -> 安全检查 -> 执行验证 -> trace -> eval
```

然后逐步抽象成通用 runtime 模型。

## 十、建议的实践路线

### 阶段 E0：框架与服务对照阅读

目标：不写大代码，先建立对照表。

产出：

- 本文档。
- 3-5 个框架的核心抽象对比。
- 项目 E 最小范围说明。

重点阅读：

- LangGraph：state、checkpoint、interrupt。
- OpenAI Agents SDK：guardrails、tracing、handoffs。
- Claude Code Skills：Skill 包结构。
- Langfuse / Phoenix：trace 和 eval 数据模型。
- Promptfoo：red team 和 eval 样本组织。

### 阶段 E1：统一 Trace 数据模型

目标：先把 D-lite 的 JSONL trace 升级为通用 trace schema。

最小结构：

```text
TraceRun
TraceSpan
LLMCall
ToolCall
ArtifactEvent
GuardrailEvent
EvaluationEvent
ApprovalEvent
```

验收标准：

- D-lite 每次运行都能生成完整 trace。
- 每个 attempt 有 span。
- 每次 LLM 调用记录 provider、model、latency、token 或估算 token。
- 每次工具调用记录输入、输出、耗时和风险等级。
- 最终状态区分 passed、failed、blocked、needs_human。

### 阶段 E2：Artifact Protocol

目标：用结构化产物替代长文本交接。

最小产物：

| Artifact | 用途 |
|----------|------|
| ErrorSummary | 错误分类和压缩 traceback |
| PatchProposal | 修复建议 |
| SafetyReport | 安全检查结果 |
| VerificationResult | 验证结果 |
| RunSummary | 一次任务的最终摘要 |

验收标准：

- 每个 artifact 有 schema。
- 每个 artifact 可以落盘。
- 每个 artifact 可以在 trace 中引用。
- 下游节点只读取 artifact，不解析自由文本。

### 阶段 E3：Tool Governance

目标：工具调用进入权限模型。

最小字段：

| 字段 | 说明 |
|------|------|
| tool_name | 工具名称 |
| description | 工具用途 |
| input_schema | 参数 schema |
| risk_level | read / workspace_write / external_write / destructive |
| allowed_paths | 文件范围 |
| requires_approval | 是否需要人工确认 |
| timeout | 超时 |
| audit | 是否记录审计 |

验收标准：

- 高风险工具默认不能自动调用。
- 外部写操作进入 approval。
- 危险操作进入 blocked。
- 所有工具调用都有 trace。

### 阶段 E4：Guardrails

目标：把安全和质量边界做成独立 runtime policy。

最小 guardrails：

- JSON schema validation。
- patch path scope check。
- AST dangerous call check。
- max attempts。
- timeout。
- budget。
- prompt injection 样本测试。
- blocked / needs_human 状态。

验收标准：

- Guardrail 失败不会被当成普通 failed。
- 安全拒绝被记录为 blocked。
- 需要人工确认被记录为 needs_human。
- guardrail event 可以被 trace 回放。

### 阶段 E5：Skills Registry

目标：验证“Skills + Guardrails”思想。

最小 skills：

| Skill | 作用 |
|-------|------|
| error-classification | 将错误压缩成稳定分类 |
| safe-patch-proposal | 输出结构化修复建议 |
| sandbox-verification | 执行验证并产出结果 |
| trace-review | 从 trace 生成复盘摘要 |

验收标准：

- 每个 Skill 有 `SKILL.md`。
- Skill 有触发说明、输入契约、输出契约和失败处理。
- Runtime 能读取 Skill metadata。
- Skill 执行结果进入 trace。

### 阶段 E6：Evaluation Runner

目标：把失败样本和安全样本变成回归测试。

最小 eval 集：

- D-lite 的 8 个 challenge tasks。
- 10 个 prompt injection 样本。
- 10 个工具越权样本。
- 5 个 schema 破坏样本。
- 5 个成本/循环控制样本。

验收标准：

- 每次 runtime 改动都能跑 eval。
- 输出 success rate、blocked rate、needs_human rate、平均尝试次数、平均 latency。
- 每个失败样本有 trace 链接。

### 阶段 E7：外部平台适配器

目标：在本地数据模型稳定后，再接入外部工具。

候选适配器：

| 适配器 | 目标 |
|--------|------|
| Langfuse exporter | 导出 trace / generation / score |
| Phoenix OTLP exporter | 用 OpenTelemetry 方式记录 trace |
| LangGraph runner | 用 LangGraph 实现同样 runtime loop |
| Promptfoo eval adapter | 跑红队和 prompt eval |

验收标准：

- 外部平台是可替换 adapter，不污染核心 runtime。
- 本地 JSONL / SQLite 仍然是最低可用记录。
- 没有外部服务时项目仍可运行。

## 十一、选型原则与风险提示

### 11.1 选型原则

| 原则 | 解释 |
|------|------|
| 先状态，后框架 | 没想清楚状态模型时，上框架只会把混乱固化 |
| 先 trace，后优化 | 没有 trace 的优化基本靠猜 |
| 先 artifact，后多 Agent | 没有结构化交接，多 Agent 只是在传长文本 |
| 先 guardrails，后工具扩张 | 工具越多，越需要权限和边界 |
| 先本地可复现，后云托管 | 云托管不应掩盖本地不可复现的问题 |
| 先最小闭环，后平台化 | 学习项目最怕一开始追求通用平台 |
| 先 eval 数据，后 prompt 微调 | 没有回归集，prompt 改动无法判断好坏 |

### 11.2 风险提示

| 风险 | 表现 | 应对 |
|------|------|------|
| 框架幻觉 | 以为接入框架就等于生产可用 | 明确任务契约、trace、eval、guardrails |
| 平台遮蔽 | 低代码平台隐藏了关键运行时细节 | 只做对照研究，不作为主线 |
| 多 Agent 失控 | 角色越多越混乱 | artifact-first，限制轮次和职责 |
| 工具越权 | Agent 调用不该调用的工具 | tool registry + permission policy |
| 安全后补 | 等出问题再补 guardrails | guardrails 前置为 runtime 层 |
| 观测不足 | 失败后无法复盘 | trace schema 从第一天就建立 |
| 云依赖过早 | 大量时间耗在认证、部署和账单 | 先本地最小闭环 |
| 评估空心化 | eval 只有主观总结 | 构造失败样本、攻击样本和回归集 |

### 11.3 最终推荐组合

对当前学习项目，推荐组合是：

```text
主线：自研最小 Runtime 骨架 + LangGraph 对照
观测：本地 trace schema + Langfuse 或 Phoenix adapter
安全：本地 deterministic guardrails + Promptfoo 红队样本
技能：Claude Code Skills 风格的本地 Skill registry
人工介入：本地 ApprovalRequest / ApprovalDecision
云服务：只做研究对照，不作为第一阶段依赖
```

如果必须选一个主框架：

```text
优先 LangGraph。
```

原因：

- 它最贴近状态机和 runtime 思维。
- 它能显式表达恢复、循环、分支和人工介入。
- 它和项目 C / D-lite 的经验自然衔接。
- 它不会像低代码平台那样隐藏太多细节。

如果必须选一个观测工具：

```text
优先 Langfuse 或 Phoenix。
```

原因：

- 二者都适合 trace/eval。
- 都能帮助把“感性调试”变成“可复盘数据”。
- Phoenix 更贴近 OpenTelemetry，本地开源体验强。
- Langfuse 的 LLM 产品化能力更完整。

如果必须选一个安全测试工具：

```text
优先 Promptfoo。
```

原因：

- 它可以把攻击样本变成回归测试。
- 它适合 agent red teaming。
- 它和项目 E 的 eval runner 目标一致。

## 参考资料

### Agent 编排 / Runtime 框架

- [LangGraph 官方文档](https://docs.langchain.com/langgraph)
- [OpenAI Agents SDK 文档](https://platform.openai.com/docs/guides/agents-sdk/)
- [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Google Agent Development Kit 文档](https://google.github.io/adk-docs/)
- [Google ADK 部署文档](https://google.github.io/adk-docs/deploy/)
- [Microsoft Agent Framework 概览](https://learn.microsoft.com/en-us/agent-framework/overview/)
- [Semantic Kernel Agent Framework](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/)
- [AutoGen AgentChat 文档](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html)
- [CrewAI 文档](https://docs.crewai.com/introduction)
- [CrewAI Flows](https://www.crewai.com/crewai-flows)
- [LlamaIndex Agents](https://docs.llamaindex.ai/en/stable/use_cases/agents/)
- [LlamaIndex Multi-agent Workflows](https://docs.llamaindex.ai/en/stable/understanding/agent/multi_agent/)
- [Pydantic AI Agent 文档](https://pydantic.dev/docs/ai/core-concepts/agent/)

### 低代码与托管服务

- [Dify Agent 文档](https://docs.dify.ai/en/use-dify/build/agent)
- [Dify Workflow Agent Node](https://docs.dify.ai/en/guides/workflow/node/agent)
- [Coze Studio GitHub](https://github.com/coze-dev/coze-studio)
- [Amazon Bedrock Agents 用户指南](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Amazon Bedrock Agents API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_Operations_Agents_for_Amazon_Bedrock.html)
- [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview)
- [Microsoft Copilot Studio 文档](https://learn.microsoft.com/en-us/microsoft-copilot-studio)
- [Google ADK Agent Engine 部署](https://google.github.io/adk-docs/deploy/agent-engine/)
- [阿里云百炼智能体应用](https://help.aliyun.com/zh/model-studio/single-agent-application)
- [百度千帆 Agent 开发平台](https://cloud.baidu.com/doc/APPBUILDER/index.html)
- [腾讯云智能体开发平台](https://cloud.tencent.com/document/product/1759)
- [华为云 AgentArts](https://www.huaweicloud.com/product/agentarts.html)
- [华为云 AgentArts 最新动态](https://support.huaweicloud.com/function-agentarts0/index.html)
- [火山引擎：Coze Studio 与 Coze Loop 开源说明](https://developer.volcengine.com/articles/7531969920030556203)
- [讯飞星辰 Agent 平台介绍](https://www.xfyun.cn/doc/spark/Agent01-%E5%B9%B3%E5%8F%B0%E4%BB%8B%E7%BB%8D.html)
- [京东 JoyAgent-JDGenie](https://github.com/jd-opensource/joyagent-jdgenie)

### Trace、Evaluation 与 Observability

- [Langfuse 文档](https://langfuse.com/docs/)
- [Arize Phoenix 文档](https://arize.com/docs/phoenix)
- [Braintrust Remote Evals](https://www.braintrust.dev/docs/evaluate/remote-evals)
- [Braintrust Agent Evaluation](https://www.braintrust.dev/learn/ai-agent-evaluation/v0)

### Guardrails、安全与红队测试

- [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo-guardrails/index.html)
- [Guardrails AI Guard](https://guardrailsai.com/guardrails/docs/concepts/guard)
- [Lakera Guard API](https://docs.lakera.ai/docs/api/guard)
- [Lakera Prompt Defense](https://docs.lakera.ai/docs/prompt-defense)
- [Promptfoo LLM Red Teaming](https://www.promptfoo.dev/docs/guides/llm-redteaming/)
- [Promptfoo Agent Red Teaming](https://www.promptfoo.dev/docs/red-team/agents/)

### Durable Execution、HITL、工具协议与 Skills

- [Temporal 文档](https://docs.temporal.io/)
- [HumanLayer](https://humanlayer.systems/index-en)
- [Model Context Protocol 官方文档](https://modelcontextprotocol.io/docs/)
- [Anthropic MCP 文档](https://docs.anthropic.com/en/docs/mcp)
- [Claude Code MCP 文档](https://code.claude.com/docs/en/mcp)
- [Claude Code Permissions](https://code.claude.com/docs/en/permissions)
- [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills)
- [Claude Code How It Works](https://code.claude.com/docs/en/how-claude-code-works)
