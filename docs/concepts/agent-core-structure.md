# Agent 系统核心结构：模型、工具、编排、状态与运行时

> 更新时间：2026-05-19
>
> 本文对 Agent 系统内部核心结构做阶段性梳理。它不把当前 `agents-learn` 项目的实践当作完整标准，而是以主流研究、厂商白皮书和框架文档中的共识为主要依据；当前项目经验只作为观察样本、反例和启发。本文的核心判断是：Agent 的一阶结构应先从模型、工具和编排循环理解；上下文、记忆、状态、产物、trace 和 runtime 是围绕这三者展开的工程化支撑。它和 `agent-system-boundaries.md` 互补：后者讨论生产级 Agent 的外部工程边界，本文讨论 Agent 系统内部的组成方式。

## 目录

- [一、文档定位](#一文档定位)
- [二、权威共识：Agent = Model + Tools + Orchestration](#二权威共识agent--model--tools--orchestration)
- [三、Model：模型作为决策器](#三model模型作为决策器)
- [四、Tools：工具作为外部世界接口](#四tools工具作为外部世界接口)
- [五、Orchestration：编排循环与行动控制](#五orchestration编排循环与行动控制)
- [六、Context / State / Memory：信息与状态层](#六context--state--memory信息与状态层)
- [七、Artifact / Trace：结构化产物与可复盘执行](#七artifact--trace结构化产物与可复盘执行)
- [八、Agent 类型谱系：核心结构的组合形态](#八agent-类型谱系核心结构的组合形态)
- [九、Agent 范式：行动如何被组织](#九agent-范式行动如何被组织)
- [十、多 Agent 协作的真实边界](#十多-agent-协作的真实边界)
- [十一、Runtime Core：公共运行环境](#十一runtime-core公共运行环境)
- [十二、设计 Agent 时应先回答的问题](#十二设计-agent-时应先回答的问题)
- [十三、阶段性结论](#十三阶段性结论)
- [参考资料](#参考资料)

## 一、文档定位

本文需要避免一个常见误区：用某个学习项目、某个 demo、某个框架样例来定义 Agent 的整体结构。当前项目中的实践很多，但完成度并不一致；有些是成功闭环，有些是探索性实验，有些只是文档研究。因此，本文采用三层依据：

| 层次 | 用途 | 可信度 |
|------|------|--------|
| 研究论文和厂商白皮书 | 提供核心概念、模式和抽象边界 | 高 |
| 主流框架文档 | 观察工程实现如何抽象 agent、tool、state、memory、guardrail、trace | 较高 |
| 当前项目实践 | 作为经验样本，帮助理解这些概念在具体任务中如何暴露问题 | 启发性，不作为标准 |

外部资料中已经形成一些相对稳定的共识：

| 来源 | 对本文的启发 |
|------|--------------|
| Anthropic `Building effective agents` | 区分 workflow 和 agent，强调 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer 等模式；同时强调工具接口和可观察规划的重要性。 |
| Google Agents 白皮书 | 将 Agent 拆成 model、tools、orchestration layer，说明模型、外部世界和控制循环之间的关系。 |
| OpenAI Agents SDK | 将 agents、tools、handoffs、guardrails、human review、results/state、tracing/evaluation 作为工程化 agent 的核心构件。 |
| LangGraph | 把 durable execution、streaming、human-in-the-loop、memory、trace 和 deployment 作为复杂 agent orchestration 的关键能力。 |
| CrewAI / AutoGen | 展示多 Agent 系统中 role、task、tool、memory、knowledge、structured output、human/tool/code integration 等工程抽象。 |
| ReAct / Reflexion 论文 | 说明 reasoning-action-observation 循环、外部反馈、自我反思和动态记忆在 Agent 行为中的作用。 |
| MCP | 提供一种工具和外部数据源连接协议的方向，说明工具接入正在从项目内临时实现走向标准化。 |

当前 `agents-learn` 项目仍然有价值，但它在本文中的位置应当是“验证和启发”，不是“论证根基”。例如：

- `01-core-concepts`：工具、Prompt、Memory 等基础组件。
- `03-langgraph-agent`：状态机和 ReAct。
- `04-multi-agent`、`07-crewai-intro`、`08-autogen-intro`、`11-metagpt-sop`：多 Agent 和角色协作。
- `05-final-project`、项目 A、`10-llamaindex-agent`：RAG / Self-RAG / Agentic RAG。
- `12-autonomous-agents`：自主循环和任务队列。
- `13-skill-library-agent`：技能库和经验沉淀。
- 项目 C：自主调研和长任务。
- 项目 D-lite：代码执行、自愈和安全边界。
- 项目 E：Agent Runtime 与治理底座。
- `architecture-deep-dives`：模型、数据、分布式状态、评估安全等底层工程。

这些项目反复触碰同一组问题：

```text
Agent 如何理解任务？
Agent 如何保存和使用上下文？
Agent 如何调用工具并控制副作用？
Agent 如何在长任务中保持状态？
Agent 如何把经验沉淀为可复用能力？
Agent 如何被 Runtime 管理，而不是每个项目重写一遍公共能力？
```

本文的目标不是定义唯一标准，而是把这些问题组织成一个可讨论的结构。

## 二、权威共识：Agent = Model + Tools + Orchestration

综合 Google Agents 白皮书、Anthropic agentic system 文章、OpenAI Agents SDK 和 LangGraph 文档后，一个更稳的核心抽象是：

```text
Agent = Model + Tools + Orchestration
```

这三者是 Agent 的一阶结构。

| 核心部分 | 中文理解 | 职责 | 关键问题 |
|----------|----------|------|----------|
| Model | 模型 / 决策器 | 理解目标、生成推理、选择动作、生成输出 | 模型是否具备足够能力，是否能遵循工具协议和任务约束 |
| Tools | 工具 / 外部世界接口 | 连接数据、系统、API、代码执行环境和业务动作 | 工具定义是否清楚，权限和副作用是否受控 |
| Orchestration | 编排 / 控制循环 | 管理上下文、步骤、状态、工具调用、观察结果和停止条件 | 控制流是否可预测、可恢复、可终止 |

如果只看模型调用，很容易把 Agent 简化成：

```text
prompt -> LLM -> answer
```

但真实 Agent 更接近：

```text
goal
  -> context assembly
  -> model decision
  -> tool/action
  -> observation
  -> state/artifact update
  -> next step or stop
```

这也是为什么 Google 将工具视为连接模型和外部世界的桥梁，将 orchestration layer 描述为摄入信息、内部推理、决定下一步行动的循环；Anthropic 则进一步区分 workflow 和 agent：workflow 走预定义路径，agent 在循环中根据环境反馈决定下一步。

在这个基础上，Agent 的二阶工程结构才展开为：

| 工程结构 | 归属 | 作用 |
|----------|------|------|
| Context | Orchestration / Model 输入 | 为当前决策装配必要信息 |
| Memory | Orchestration / Runtime | 保存跨轮次、跨任务可复用的信息 |
| State | Orchestration / Runtime | 保存任务阶段、步骤、预算和恢复点 |
| Artifact | Orchestration / Runtime | 保存结构化中间产物和最终产物 |
| Trace | Runtime / Observability | 记录模型、工具、状态和产物变化 |
| Guardrails | Runtime / Governance | 在输入、输出、工具和高风险动作前做约束 |
| Human-in-the-loop | Runtime / Governance | 在低置信度或高风险场景中暂停并请求人工判断 |
| Evaluation | Runtime / Quality | 用规则、测试、LLM Judge 或人工复核判断质量 |

因此，本文后面讨论的类型、上下文、记忆、工具、状态和 Runtime，不应被理解为并列的“Agent 定义要素”。更合理的层次是：

```text
第一层：Model + Tools + Orchestration
第二层：Context + State + Memory + Artifact + Trace
第三层：Guardrails + Evaluation + Human Review + Deployment
```

**本节小结**：Agent 的智能来自模型，行动能力来自工具，持续任务能力来自编排；可靠性则来自状态、trace、guardrails、评估和人工介入等工程支撑。

## 三、Model：模型作为决策器

模型是 Agent 的推理和生成核心，但模型本身不等于 Agent。Google 白皮书把模型放在 Agent 的核心组成中，同时明确指出模型通常并不知道具体工具配置、编排方式和业务状态；这些需要由 Agent 系统在运行时提供。

在 Agent 中，模型通常承担这些职责：

| 职责 | 说明 |
|------|------|
| 理解目标 | 将用户目标、系统约束和当前状态转化为可执行意图 |
| 生成推理 | 在当前上下文中分析问题、比较方案、处理不确定性 |
| 选择动作 | 决定是否调用工具、调用哪个工具、以什么参数调用 |
| 生成产物 | 输出回答、计划、补丁、报告、结构化 artifact 等 |
| 处理反馈 | 根据观察结果、工具返回、测试失败或评估反馈调整下一步 |

但模型也有清晰限制：

- 模型不知道没有进入上下文的信息。
- 模型不能直接访问外部世界，只能通过工具。
- 模型输出具有不确定性，需要通过 schema、validator、trace 和 evaluation 管理。
- 模型擅长开放判断，但不适合承担不可逆动作的最终审批。
- 模型的长期能力不等于当前任务状态，状态和记忆必须由系统显式管理。

因此，设计 Agent 时不应把所有问题都交给 prompt。更合理的方式是：

```text
模型负责开放判断，
系统负责边界、状态、工具、验证和恢复。
```

## 四、Tools：工具作为外部世界接口

Agent 的能力边界主要由工具决定。Google 白皮书将工具称为连接模型和外部世界的桥梁；MCP 的出现也说明，工具和数据源接入正在从项目内临时实现走向标准化协议。

模型本身只能生成文本或结构化调用意图，真正改变外部世界的是工具：

- 文件读写。
- Shell 命令。
- 浏览器。
- 数据库。
- 搜索。
- API。
- Git。
- 部署系统。
- 消息系统。
- 多模态输入输出。

因此，工具不是简单函数列表，而是一套动作模型。

每个工具至少应描述：

| 维度 | 需要说明的问题 |
|------|----------------|
| 能力 | 工具能做什么，不能做什么 |
| 输入 schema | 参数类型、必填字段、边界值 |
| 输出 schema | 返回结构、错误结构、可引用字段 |
| 副作用 | 是否读、写、删除、部署、发消息、扣费 |
| 权限 | 可访问哪些路径、服务、凭证和数据 |
| 风险等级 | 是否需要人工审批 |
| 幂等性 | 重试是否安全 |
| 超时和重试 | 失败后如何处理 |
| 可观测性 | 是否记录输入、输出、耗时和错误 |

D-lite 的意义就在于它触碰了最危险也最真实的一层：执行。只要 Agent 能执行代码、写文件、调用系统命令，就必须把安全、验证和失败终态放到核心位置。

## 五、Orchestration：编排循环与行动控制

Orchestration 是 Agent 的控制循环。它负责把目标、上下文、模型决策、工具调用、观察结果、状态更新和停止条件组织起来。

一个常见的长任务循环是：

```text
Goal
  -> Context Assembly
  -> Model Decision
  -> Tool Call
  -> Observation
  -> State / Artifact Update
  -> Review
  -> Next Step or Stop
```

Anthropic 的重要区分是：workflow 和 agent 都属于 agentic system，但 workflow 走预定义路径，agent 会在运行中根据反馈决定后续步骤。这个区分比“是不是用了多个 Agent”更基础。

控制流可以有不同强度：

| 控制方式 | 特征 | 适合场景 |
|----------|------|----------|
| 固定 pipeline | 步骤预先确定 | 表单处理、固定报告生成 |
| 状态机 | 状态和跳转显式定义 | 多分支、可恢复流程 |
| Planner + Executor | 先计划再执行 | 调研、代码任务、复杂分析 |
| Supervisor + Workers | 总控拆分并分配任务 | 并行研究、多源信息收集 |
| Autonomous Loop | Agent 自行决定下一步 | 开放探索、实验性任务 |

Planning 是 Agent 把目标拆成步骤的能力，Control 是系统约束 Agent 如何执行这些步骤的能力。但计划不是越复杂越好。很多 Agent 的计划只是看起来合理，实际执行时仍然偏离目标。

有效计划应该满足：

- 可执行：每一步能落到具体工具或产物。
- 可检查：能判断该步是否完成。
- 可中断：中途停止不会丢失关键信息。
- 可恢复：有 checkpoint 和状态。
- 可调整：工具失败或证据不足时能改计划。
- 有预算：限制 token、时间、重试次数和工具调用。
- 有停止条件：知道什么时候完成、失败或 blocked。

越自主的编排，越需要预算、终止条件、trace、guardrails 和人工介入。

## 六、Context / State / Memory：信息与状态层

Context、State 和 Memory 经常被混在一起，但它们承担不同职责。

| 概念 | 时间范围 | 主要用途 |
|------|----------|----------|
| Context | 当前 step / 当前轮次 | 支撑当前模型决策 |
| State | 当前任务生命周期 | 支撑任务推进、恢复和复盘 |
| Memory | 跨任务 | 复用经验、偏好、知识和策略 |

### 6.1 Context：当前决策的工作视图

上下文是 Agent 当前一次决策所看到的信息。它不是完整聊天记录，也不是长期记忆本身。

关于上下文类型分层、生命周期、Context Builder、上下文污染治理和后续实现优先级，详见专题文档：[Agent 上下文工程：从 Prompt 拼接到可治理的工作视图](./agent-context-engineering.md)。

更准确地说：

```text
上下文是为了当前 step 构造出来的工作视图。
```

上下文通常包含：

- 系统指令。
- 当前任务目标。
- 当前 step。
- 相关历史摘要。
- 必要证据。
- 工具定义。
- 可用约束。
- 上一步观察结果。
- 当前要产出的 artifact schema。

上下文管理的难点在于：模型只能基于看到的内容做判断，但看到太多内容又会造成噪声、成本和注意力分散。

常见问题包括：

| 问题 | 表现 | 后果 |
|------|------|------|
| 上下文膨胀 | 所有历史都追加进 prompt | 成本升高，关键信息被淹没 |
| 上下文污染 | 旧错误、低质量输出、无关讨论进入 prompt | 模型延续错误假设 |
| 证据缺失 | 检索结果、工具输出或约束没有进入 prompt | 模型凭空补全 |
| 工具描述过载 | 工具太多、描述太长 | 模型选错工具或不调用工具 |
| 多 Agent 交接不清 | 下游只看到上游自由文本 | 责任边界模糊，错误难定位 |

更合理的上下文治理方式是：

```text
完整历史进入 Trace，
关键状态进入 RuntimeState，
中间结果进入 Artifact，
当前决策只装配必要上下文。
```

### 6.2 State：任务执行的当前位置

状态描述任务现在处于哪里。典型状态包括：

- task id。
- 当前阶段。
- 当前 step。
- 已完成 step。
- 失败 step。
- 当前预算。
- 可用工具。
- 人工审批状态。
- 上下文摘要。
- 最终状态：passed、failed、blocked、cancelled。

状态服务于执行、恢复和复盘。没有状态，长任务只能依赖不断增长的聊天历史；一旦中断、失败或上下文过长，就很难可靠恢复。

### 6.3 Memory：跨任务复用的经验系统

很多系统把“记忆”理解为“把对话存进向量库”。这只能解决一小部分问题，而且容易带来污染。

更有价值的记忆包括：

- 用户偏好：输出风格、常用技术栈、风险偏好。
- 项目约定：目录结构、测试命令、代码风格、配置方式。
- 领域知识：业务术语、数据字典、接口规范。
- 成功经验：哪些策略在某类任务中有效。
- 失败案例：哪些工具组合、prompt 或流程导致过失败。
- 技能定义：可重复调用的 procedure、script、template 或 MCP tool。
- 评估样本：历史问题、期望答案、回归用例。

记忆管理的关键不是“存得多”，而是“能不能在正确时机取出正确内容，并且知道它是否仍然可信”。

因此，记忆至少需要这些元信息：

| 元信息 | 作用 |
|--------|------|
| 来源 | 判断记忆来自用户、工具、模型输出还是人工确认 |
| 时间 | 判断是否过期 |
| 适用范围 | 区分全局偏好、项目约定、任务局部信息 |
| 置信度 | 区分事实、推断、偏好和暂定结论 |
| 版本 | 处理 prompt、工具、代码和业务规则变化 |
| 验证方式 | 判断这条记忆是否经过测试、人工确认或工具验证 |

`13-skill-library-agent` 的启发在于：Agent 的长期成长不一定来自越来越长的自然语言记忆，更可能来自：

```text
经验 -> 技能 -> 可验证调用 -> 版本化复用
```

## 七、Artifact / Trace：结构化产物与可复盘执行

Artifact 和 Trace 是 Agent 从“会执行”走向“可验证、可复盘”的关键结构。

### 7.1 Artifact

Artifact 是 Agent 产出的结构化中间物或最终产物。

常见 artifact 包括：

- Research Plan。
- Evidence Table。
- Query Rewrite。
- Draft Report。
- Review Rubric。
- Patch。
- Test Result。
- Runtime Trace Summary。
- Decision Record。

Artifact 的价值在于：它可以被验证、引用、传递和复用。

多 Agent 系统尤其应该通过 artifact 交接，而不是让下游 Agent 阅读上游 Agent 的长篇自然语言输出后自行理解。

### 7.2 Trace

Trace 记录任务是如何执行的。

它应该包含：

- step 输入。
- 模型输出。
- 工具调用。
- 工具参数。
- 工具返回。
- 错误。
- 重试。
- 人工介入。
- artifact 生成记录。
- 预算和耗时。

Trace 服务于复盘、调试、审计和评估。

二者关系可以概括为：

```text
Artifact 负责交接和验证。
Trace 负责复盘和审计。
```

## 八、Agent 类型谱系：核心结构的组合形态

Agent 类型不应放在核心结构之前理解。类型只是 `Model + Tools + Orchestration` 在不同任务场景中的组合形态。

不同 Agent 类型也不是互斥分类，而是不同能力重点。一个真实项目经常同时具备多个类型特征。下面的分类不是来自当前项目的目录结构，而是综合主流论文、框架和产品形态后得到的工程分类。

| 类型 | 典型来源 / 代表实现 | 核心能力 | 主要风险 |
|------|----------------------|----------|----------|
| Tool-use Agent | ReAct、Google Agents、OpenAI Agents SDK、MCP | 以工具为核心扩展模型行动能力 | 工具误用、参数错误、越权动作 |
| RAG / Knowledge Agent | RAG、LlamaIndex、LangChain、GraphRAG | 以检索和知识接入扩展模型上下文 | 检索失败、证据不忠实、引用不可靠 |
| Workflow Agent | Anthropic workflow patterns、Dify、Coze、CrewAI Flows | 以预定义编排控制步骤 | 灵活性不足，复杂分支会膨胀 |
| State Machine Agent | LangGraph、Temporal 风格 durable workflow | 以显式状态和条件转移控制循环 | 状态设计复杂，节点边界难定 |
| Multi-Agent | AutoGen、CrewAI、MetaGPT、orchestrator-workers | 多角色、多工具或多上下文协作 | 角色空转、上下文污染、责任不清 |
| Autonomous Agent | BabyAGI、AutoGPT、通用任务型 agent | 由模型在循环中决定更多中间步骤 | 目标漂移、成本失控、停止困难 |
| Code Agent | Claude Code、OpenAI Codex / coding agents、smolagents | 将代码库、shell、测试和 patch 作为工具环境 | 副作用高、安全风险大、验证困难 |
| Reflection / Self-improving Agent | Reflexion、evaluator-optimizer | 根据反馈调整策略或输出 | 反馈不可靠时会放大错误 |
| Skill Library Agent | Voyager、Claude Skills、MCP tool ecosystem | 把经验沉淀为可复用技能 | 技能质量、触发条件和版本治理困难 |
| Runtime-governed Agent | OpenAI Agents SDK、LangGraph、企业 agent platform | 由 Runtime 管理状态、工具、权限、trace | Runtime 抽象过重或耦合具体业务 |
| Multimodal Agent | GPT-4o / Gemini / Claude 多模态、语音和视觉 agent | 处理语音、图像、视频和生成结果 | 输入可信度、成本、隐私和安全边界 |

所以设计 Agent 时，不应只问“它是哪一种 Agent”，而应问：

```text
它需要哪些能力组合？
哪些能力属于业务 Agent？
哪些能力应该下沉到 Runtime？
哪些能力应该以 Skill 或 Tool 的形式复用？
```

## 九、Agent 范式：行动如何被组织

Agent 类型描述“Agent 做什么”，范式描述“Agent 如何组织行动”。

| 范式 | 代表 | 适合场景 | 主要风险 |
|------|------|----------|----------|
| 编排式 workflow | Dify、Coze、固定 pipeline | 步骤清晰、路径稳定、业务可预期 | 灵活性弱，复杂分支会膨胀 |
| 状态机 | LangGraph、durable workflow | 有循环、恢复、条件跳转和终止要求 | 前期建模成本高 |
| ReAct | ReAct 论文、工具调用 Agent | 需要边想边做、边观察边调整 | 容易陷入循环或过度调用工具 |
| Plan and Execute | 调研、长任务、代码任务 | 目标可拆解，需要多步执行 | 计划可能空泛，执行中会偏离 |
| Reflection / Evaluator-optimizer | 报告生成、自愈、质量提升 | 有明确评价标准，需要迭代改进 | 评估器不稳会放大错误 |
| Orchestrator-workers | 多 Agent 调研、多源信息收集 | 可并行拆分任务 | 汇总、去重和质量控制复杂 |
| 角色协作 | CrewAI、AutoGen、MetaGPT | 需要职责隔离或模拟组织流程 | 容易变成角色名包装的 prompt 串联 |
| 自主循环 | BabyAGI、AutoGPT、通用自主 Agent | 目标开放、路径难预先定义 | 停止困难，成本和目标漂移明显 |
| Skills + Guardrails | Claude Skills、MCP、OpenAI Agents SDK guardrails | 能力需要复用，同时风险需要约束 | 需要设计稳定接口、权限和版本 |

一个重要判断是：

```text
不要用“更自主”替代“更清楚”。
```

如果任务路径清晰，优先 workflow 或状态机。如果任务路径开放，才引入更自主的 planning、reflection 或 multi-agent。自主性越高，越需要预算、终止条件、trace 和人工介入。

## 十、多 Agent 协作的真实边界

多 Agent 的价值不在于“多几个角色名”，而在于隔离不同责任、上下文、工具和评价标准。

合理的多 Agent 拆分通常基于：

- 不同信息来源。
- 不同工具权限。
- 不同专业职责。
- 不同产物类型。
- 不同质量标准。
- 并行处理需求。

不合理的多 Agent 拆分通常表现为：

- 角色名字很多，但都在做同一件事。
- 上下游只通过自由文本交接。
- Reviewer 只能给泛泛意见。
- 没有独立质量标准。
- 没有最终仲裁。
- 没有 trace 记录责任边界。

项目 B 的经验说明：多 Agent 不是质量保证机制。它只是组织任务的一种方式。

更稳定的多 Agent 应该是：

```text
Role
  + clear responsibility
  + limited context
  + controlled tools
  + structured artifact
  + independent evaluation
```

否则，多 Agent 很容易退化成：

```text
prompt A -> prompt B -> prompt C
```

这会增加复杂度，却不一定提高质量。

## 十一、Runtime Core：公共运行环境

项目 E 的关键转向是：Runtime 不应该只是评测器，也不应该只服务某一个 Agent。

更合理的定位是：

```text
不同 Agent 负责业务逻辑，
Runtime 负责公共运行能力。
```

Runtime Core 应该逐步承载：

| Runtime 能力 | 作用 |
|--------------|------|
| RuntimeState | 保存任务状态、预算、阶段和恢复点 |
| Step | 表达一次可观测、可验证的执行单元 |
| Tool Registry | 管理工具定义、schema、权限和风险等级 |
| Tool Policy | 控制工具能否调用、是否需要审批 |
| Artifact Store | 保存结构化产物和版本 |
| Trace Store | 记录执行过程，支持复盘和审计 |
| Context Builder | 为每个 step 装配必要上下文 |
| Memory Adapter | 管理跨任务记忆、项目约定和技能 |
| Evaluation Hook | 在关键节点做规则、测试或 LLM Judge |
| Human Intervention | 在高风险或低置信度场景停下来 |
| Provider Manager | 管理不同 LLM provider、模型、成本和延迟 |

这也是为什么“Agent Runtime”是一个宏大主题。它不是一个功能，而是一组公共能力的长期沉淀。

当前更现实的路径不是一次性做完整 Runtime，而是从最小核心开始：

```text
RuntimeState
  + Step
  + Tool
  + Artifact
  + Trace
```

然后逐步加入 policy、memory、evaluation、human-in-the-loop 和 provider governance。

## 十二、设计 Agent 时应先回答的问题

在开始写 Agent 之前，可以先回答下面的问题。

| 问题 | 意义 |
|------|------|
| 这个任务真的需要 Agent 吗？ | 如果固定流程足够，就不要引入自主性 |
| 需要什么模型能力？ | 判断模型是否能承担推理、结构化输出、工具选择和多轮反馈 |
| 需要哪些工具？工具有什么副作用？ | 决定权限、安全、审批、幂等性和观测策略 |
| 编排路径是 workflow、状态机，还是更开放的自主循环？ | 决定系统的可控性、恢复方式和复杂度 |
| Agent 的输入、输出和停止条件是什么？ | 防止目标漂移和无界循环 |
| 哪些信息进入上下文，哪些应该成为 artifact？ | 防止上下文膨胀和交接不稳定 |
| 哪些状态必须持久化？ | 支撑 checkpoint、resume 和复盘 |
| 是否需要长期记忆？记忆如何验证和过期？ | 防止错误经验长期污染 |
| 是否需要多 Agent？职责、工具和上下文是否真的不同？ | 防止无意义角色拆分 |
| 如何评估成功？ | 避免只看模型回答是否顺眼 |
| 哪些能力应该属于 Runtime？ | 避免每个 Agent 重复实现公共能力 |
| 失败时如何 blocked，而不是无限重试？ | 把不确定性变成可处理终态 |

这组问题比“选哪个框架”更重要。框架只能提供实现方式，不能替代系统边界和核心结构设计。

## 十三、阶段性结论

综合外部资料和当前项目经验，可以得到一个阶段性结论：

```text
Agent 不是更长的 prompt，
也不是更多角色的聊天，
而是运行在受控环境中的模型决策系统。
```

它的核心结构可以概括为：

```text
模型负责理解、推理和生成，
工具负责连接外部世界并执行动作，
编排负责组织上下文、步骤、状态和停止条件，
状态支撑长任务执行和恢复，
Artifact 支撑结构化交接和验证，
Trace 支撑复盘、调试和评估，
Runtime 支撑权限、治理、观测和演进。
```

这也解释了为什么开发生产级 Agent 会显得复杂。复杂性并不是偶然增加的，而是来自 Agent 本身跨越了传统软件、模型推理、工具执行、知识管理、运行时治理和安全评估多个边界。

后续继续探索时，应尽量避免两个极端：

- 把 Agent 简化成一次 LLM 调用。
- 把 Agent 设计成无边界的通用自主系统。

更可行的方向是：

```text
用明确任务边界控制范围，
用 workflow / state machine 承载确定性，
用 LLM 处理开放判断，
用 tools / skills 扩展行动能力，
用 runtime 管理状态、权限、产物、trace 和评估。
```

这不是最终答案，但可以作为当前阶段继续实践 Agent Runtime 和具体 Agent 项目的核心认知框架。

## 参考资料

- [Anthropic：Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)。用于理解 workflow 与 agent 的区别，以及 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer、tool interface 等模式。
- [Google Agents 白皮书](https://storage.ghost.io/c/dc/a8/dca8ae32-7ed6-405a-b948-680b55c8f3dc/content/files/2025/01/Whitepaper-Agents---Google.pdf)。用于理解 model、tools、orchestration layer 这三个核心组成。
- [OpenAI Agents SDK 文档](https://developers.openai.com/api/docs/guides/agents)。用于理解 agent、tool、handoff、guardrail、human review、state、trace、evaluation 等工程抽象。
- [LangGraph 文档](https://docs.langchain.com/oss/python/langgraph/overview)。用于理解 durable execution、streaming、human-in-the-loop、memory、trace 和 long-running workflow。
- [CrewAI 文档](https://docs.crewai.com/)。用于理解 agents、crews、flows、memory、knowledge、structured outputs、guardrails 和 observability。
- [Microsoft AutoGen 文档](https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/)。用于理解 conversable agents、多 Agent 对话、LLM / human / tool / code execution 集成。
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)。用于理解 reasoning trace 与 action / observation 交替的 Agent 行为模式。
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)。用于理解反馈、自我反思、动态记忆对 Agent 行为改进的作用。
- [Anthropic：Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol?cb=zapier)。用于理解外部工具和数据源连接从定制集成走向协议化的趋势。
