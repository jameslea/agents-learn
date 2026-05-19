# Agent Runtime 哲学：从 Agent 能力到运行时治理

> 让 Agent 可控、可复盘、可演进。
>
> 本文是 A/B/C/D-lite 实践后的阶段性方法论沉淀。重点不是再设计一个项目，而是解释：为什么 Agent 开发越往后越不像“功能开发”，以及哪些能力应沉淀为框架或运行时。

## 目录

- [文档定位](#文档定位)
- [一、核心判断](#一核心判断)
- [二、前沿共识：Agent 正在从 demo 走向 runtime](#二前沿共识agent-正在从-demo-走向-runtime)
- [三、Agent 产品化的非功能能力清单](#三agent-产品化的非功能能力清单)
- [四、范式不是宗教，而是工具箱](#四范式不是宗教而是工具箱)
- [五、从“万能 Agent”转向“Skills + Guardrails”](#五从万能-agent转向skills--guardrails)
- [六、Agent Runtime 的八层模型](#六agent-runtime-的八层模型)
- [七、A-D 实践后的模式判断](#七a-d-实践后的模式判断)
- [八、从项目 E 到独立 Runtime 项目](#八从项目-e-到独立-runtime-项目)
- [九、设计原则与反模式](#九设计原则与反模式)
- [十、后续探索问题](#十后续探索问题)
- [参考资料](#参考资料)

## 文档定位

本文和 `agent-design-methodology.md` 互补：

- `agent-design-methodology.md` 解决“如何设计一个可控 Agent 系统”的问题，重点是 workflow、state、artifact、tool 和 eval 的设计顺序。
- 本文解决“哪些能力应该沉淀为 runtime/governance，而不是每个 Agent 重做一遍”的问题，重点是 Skills、Guardrails、trace、状态、评估和运行时治理。

换句话说，前者偏项目设计方法，本文偏长期工程哲学和能力沉淀。

## 一、核心判断

当前 Agent 开发没有统一套路，也不应急于追求一个统一套路。更现实的方向是：把 Agent 看成运行在受控 runtime 中的动态决策单元，而不是一个靠 prompt 变聪明的完整产品。

成熟 Agent 系统的关键不只是模型能力，而是这些非功能能力：

- 状态持久化与恢复。
- 上下文治理。
- 工具权限和参数约束。
- 安全边界和失败终态。
- 结构化产物协议。
- 可回放 trace。
- 评估和回归测试。
- 人类介入点。
- 成本、延迟和预算控制。
- 部署与版本治理。

这些能力不应在每个 Agent 项目里重新实现一遍。它们应该沉淀为框架、运行时、工程约束或组织级实践。

**本节小结**：Agent 产品化的核心矛盾，是模型能力越来越强，但工程边界、运行时治理和评估体系没有同步成熟。

## 二、前沿共识：Agent 正在从 demo 走向 runtime

近期不同团队的实践虽然术语不同，但方向越来越接近：Agent 产品化的难点不在“再写一个更长的 prompt”，而在于运行时和治理。

Anthropic 在 `Building effective agents` 中强调，很多有效系统并不是复杂自主 Agent，而是清晰、可组合的 workflow pattern。它区分了 workflow 和 agent：workflow 由预定义路径编排 LLM 和工具；agent 则在运行中自主决定步骤和工具调用。这个区分对工程决策很关键：多数业务任务应该先尝试 workflow，只有当路径无法预先确定时才进入更自主的 agent 模式。

Anthropic 的多 Agent 研究系统经验也说明，多 Agent 适合高价值、可并行、信息量超过单个上下文窗口的任务。它的复杂度主要来自协调、评估、可靠性和可观测性，而不是“多几个角色名”。这和项目 B 的经验一致：多角色本身不会带来稳定质量，稳定性来自边界、产物、评估和 trace。

OpenAI Agents SDK 把核心抽象收敛到 agents、handoffs、guardrails、tracing。这说明 tracing 和 guardrails 已经被视为运行时基本能力，而不是业务代码里的临时补丁。

Google Agent 白皮书把 Agent 拆成 model、tools、orchestration layer。这个三分法可以帮助我们避免把所有能力都归因于模型：模型负责推理，工具连接外部世界，编排层决定状态、循环、记忆和控制。

LangChain 对 production deep agents 的讨论进一步指出，prompt、tools、skills 只是 harness 的一部分。生产系统还需要 durable execution、memory、multi-tenancy、human-in-the-loop 和 observability。也就是说，长期复杂度在 runtime。

这些资料共同指向一个判断：

```text
Agent 的产品化路径不是 prompt engineering -> 更复杂 prompt。
更可能是 prompt/workflow -> skills/guardrails -> runtime/governance。
```

**本节小结**：不同生态的前沿实践正在收敛到同一个方向：Agent 的长期价值不只来自推理模型，而来自可组合 workflow、工具治理、trace、guardrails 和 durable runtime。

## 三、Agent 产品化的非功能能力清单

这些能力看起来“不直接完成业务功能”，但它们决定了 Agent 能不能从 demo 变成可持续运行的系统。

| 能力 | 简述 | 缺失后的典型后果 |
|------|------|------------------|
| 状态持久化 | 保存任务阶段、产物、工具调用、失败原因和恢复点 | 中断后无法恢复，重复执行副作用操作 |
| 上下文治理 | 管理短期上下文、长期记忆、压缩摘要和检索材料 | 上下文膨胀、目标漂移、成本失控 |
| 工具权限 | 定义 Agent 能调用什么工具、以什么参数、在什么条件下调用 | Agent 越权执行写操作或调用错误工具 |
| 安全边界 | 通过沙箱、静态检查、策略和终态限制高风险行为 | 仅靠 prompt 约束，无法阻止危险动作 |
| 结构化产物 | 用 schema 化 artifact 替代长对话交接 | 下游解析不稳定，无法校验和复盘 |
| 可回放 trace | 记录每轮输入、输出、工具调用、错误和决策 | 失败无法定位，优化只能靠直觉 |
| 评估体系 | 建立确定性测试、LLM judge、人类复核和回归集 | 每次改 prompt 都不知道整体变好还是变差 |
| 人工介入 | 在高风险、低置信度或不可逆动作前引入人类确认 | Agent 自动做出无法接受的业务决策 |
| 成本和延迟控制 | 跟踪 token、调用次数、模型耗时和预算 | 自主循环无限扩张，用户体验不可控 |
| 部署与版本治理 | 管理 prompt、模型、工具、schema 和运行时版本 | 线上行为不可复现，回滚和对比困难 |

这张表可以作为后续设计任何 Agent 项目的预检清单。一个任务越接近生产、外部写操作或代码执行，就越需要这些能力前置，而不是等出问题后补。

其中“上下文治理”的专题展开见：[Agent 上下文工程：从 Prompt 拼接到可治理的工作视图](./agent-context-engineering.md)。

**本节小结**：这些非功能项不是“高级优化”，而是 Agent 产品化的基础设施。越晚引入，返工成本越高。

## 四、范式不是宗教，而是工具箱

Agent 系统常见范式包括：

| 范式 | 代表平台/框架 | 核心思想 | 优点 | 风险 |
|------|----------------|----------|------|------|
| 编排式 workflow | Dify、Coze | 把任务拆成固定步骤 | 可控、可测试、易复盘 | 灵活性有限 |
| 状态机 | LangGraph | 显式建模状态和转移 | 易恢复、易限制循环 | 设计成本较高 |
| 多角色 | CrewAI、AutoGen | 多个 Agent 扮演不同职责 | 适合上下文、工具或权限隔离 | 容易变成 prompt 接龙 |
| 通用自主 Agent | Manus、Claude Code | 给目标，让 Agent 自己规划和行动 | 探索能力强 | 成本、漂移、安全风险高 |
| Evaluator-optimizer | LangGraph / 自定义评估闭环 | 生成后评估，再根据反馈改进 | 适合有明确质量标准的任务 | 评估器不稳会放大错误 |
| Orchestrator-workers | AutoGen、Anthropic multi-agent research pattern | 总控拆任务，worker 并行执行 | 适合大规模信息收集 | 合成和去重复杂 |
| Skills + Guardrails | Claude Code Skills、OpenAI Agents SDK、MCP 工具生态 | 构建可调用技能和护栏，而不是追求万能 Agent | 能力可复用，风险可控 | 需要良好的技能接口和治理 |

这里的分类不是严格边界。一个产品或框架经常同时覆盖多个范式。例如 LangGraph 既可以写状态机，也可以实现 evaluator-optimizer 或 orchestrator-workers；AutoGen 既可做多角色对话，也可做总控-执行器模式；Claude Code 既体现通用自主 Agent，也逐渐强调 Skills、工具和运行时护栏。

因此，范式选择不应按“哪个框架更强”来判断，而应按任务特征判断：

- 路径清晰、步骤固定：优先编排式 workflow。
- 需要恢复、循环和明确终止：优先状态机。
- 需要权限、上下文或工具隔离：考虑多角色。
- 目标开放、路径无法预先确定：谨慎使用通用自主 Agent。
- 有明确质量标准：加入 evaluator-optimizer。
- 能力需要复用：抽成 Skills。
- 风险不可忽略：先设计 Guardrails。

这些范式不是互斥的。一个真实系统通常会组合使用：

```text
Workflow 负责主干
State machine 负责恢复和终止
Skills 负责可复用能力
Guardrails 负责边界
Evaluator 负责质量反馈
Human-in-the-loop 负责高风险判断
Autonomous loop 只在低风险或高探索价值区域启用
```

**本节小结**：范式选择应该服务于任务形态，而不是服务于框架偏好。真正成熟的系统通常是多范式组合。

## 五、从“万能 Agent”转向“Skills + Guardrails”

早期 Agent 实验容易追求一个万能 Agent：它能规划、搜索、写代码、修复、评估、调用工具、处理异常。这种方向在 demo 中很吸引人，但工程上很快失控。

更稳健的趋势是：

```text
不要把所有能力堆进一个万能 Agent。
构建一组可被 Agent 调用的 Skills，以及一组始终生效的 Guardrails。
```

### Skills 是可复用能力单元

Skill 不只是 prompt 模板。一个合格 Skill 至少包含：

- 明确用途：解决什么问题，不解决什么问题。
- 输入契约：参数、格式、边界。
- 输出契约：结构化结果、错误类型。
- 依赖说明：需要哪些工具、文件、环境变量。
- 使用步骤：什么时候调用，调用前后如何验证。
- 示例和反例：避免被错误触发。

Skill 的价值是把“经验”从一次性对话中抽出来，变成可复用能力。

例如 D-lite 中可以沉淀出这些 Skills：

| Skill | 作用 |
|-------|------|
| `python-error-classification` | 把 traceback 压缩为稳定错误分类 |
| `safe-code-patch` | 只输出结构化 patch proposal |
| `sandbox-verification` | 在隔离目录中执行并验证结果 |
| `trace-review` | 从 JSONL trace 生成复盘摘要 |

这些能力比“写一个自愈 Agent”更可复用。

### Skills 不是“函数库”，而是经验封装

普通函数封装的是确定性逻辑。Skill 封装的是“模型如何在特定上下文中可靠完成一类任务”的经验。

因此 Skill 通常同时包含：

- 操作流程。
- 上下文选择原则。
- 工具使用规范。
- 输出 schema。
- 失败处理。
- 验证方式。

这也是为什么 Skills 比 prompt 更适合作为组织资产：prompt 往往依赖一次性上下文，Skill 则把经验压成可复用协议。

### Guardrails 是运行时边界

Guardrails 不应只靠 prompt 声明“不要做坏事”。它们应该作为运行时能力存在：

- 静态检查：AST、schema、类型、危险调用。
- 动态检查：timeout、资源限制、沙箱。
- 权限检查：工具分级、写操作确认。
- 输出检查：JSON schema、引用格式、patch 范围。
- 终态检查：`passed`、`failed`、`blocked`、`needs_human` 明确区分。

D-lite 的 `blocked` 终态是一个重要信号：安全拒绝不是失败，而是系统正确工作。

### Guardrails 不只是安全，也包括质量边界

Guardrails 容易被狭义理解为安全审查。实际上它还包括质量边界：

- 输出是否符合 schema。
- 引用是否真实存在。
- patch 是否越权修改。
- 工具调用参数是否合理。
- 成本是否超过预算。
- 循环是否超过最大轮次。
- 结果是否需要人工确认。

所以 Guardrails 不是给 Agent “踩刹车”的附属模块，而是定义系统可接受行为范围的运行时机制。

**本节小结**：长期可复用的不是某个万能 Agent，而是 Skills、Guardrails 和它们运行其上的 runtime。

## 六、Agent Runtime 的八层模型

可以把成熟 Agent 系统拆成八层：

| 层次 | 中文名称 | 作用 | 关键问题 |
|------|----------|------|----------|
| Task Contract | 任务契约层 | 定义任务输入、输出、成功标准、失败成本和人工确认点 | 这个任务怎么才算完成？ |
| Context Engineering | 上下文工程层 | 管理上下文、记忆、压缩摘要和检索材料 | 给 Agent 什么信息，什么时候压缩？ |
| Artifact Protocol | 结构化产物层 | 用结构化产物替代长对话交接 | 下游如何稳定消费结果？ |
| Tool Governance | 工具治理层 | 管理工具权限、参数和调用条件 | Agent 能做什么，不能做什么？ |
| Execution Runtime | 执行运行时层 | 管理 checkpoint、resume、timeout、retry、max steps | 中断后能否恢复？循环能否停止？ |
| Safety Runtime | 安全运行时层 | 管理 sandbox、policy、blocked、approval | 风险动作如何被拦截？ |
| Observability | 可观测性层 | 记录输入输出、工具调用、错误、成本和延迟 | 失败后能否复盘？ |
| Evaluation Loop | 评估闭环层 | 建立测试、judge、人类复核和回归集 | 改动后是否真的变好？ |

这八层不是要求一次性全部实现，而是提醒：Agent 的复杂度通常会自然落在这些位置。越早识别这些层，越不容易把业务代码写成一团运行时补丁。

推荐的产物交接模式：

```text
Input -> Agent/Node -> Artifact -> Validator -> Next Step
```

推荐的工具风险分级：

| 风险 | 示例 | 策略 |
|------|------|------|
| 只读 | 搜索、读文件、查数据库 | 允许，记录 trace |
| 内部写 | 写草稿、写 workspace 文件 | 允许，版本化和验证 |
| 外部写 | 发邮件、提交 PR、执行命令 | 沙箱、审批或人工确认 |
| 破坏性动作 | 删除数据、线上变更、支付 | 默认禁止，除非有强治理 |

**本节小结**：Agent Runtime 的价值，是把状态、上下文、工具、安全、执行、观测和评估从业务 Agent 中抽离出来。

## 七、A-D 实践后的模式判断

| 项目 | 核心教训 | 对应 runtime 能力 |
|------|----------|-------------------|
| 项目 A：RAG | RAG 不是“接一个向量库”，关键是检索质量、重排、引用边界和忠实度评估 | 检索 trace、引用支撑验证、query rewrite 评估、幻觉检测 |
| 项目 B：内容团队 | 多角色不等于高质量，角色越多，状态和交接越难 | artifact protocol、role boundary、引用验证、版本化产物、人类审核点 |
| 项目 C：自主调研 | 自主循环最大问题是目标漂移、成本失控、上下文膨胀和停止条件 | task queue、budget、checkpoint、reflection、max steps |
| 项目 D-lite：代码自愈 | 代码执行型 Agent 的核心不是生成 patch，而是安全执行和客观验证 | sandbox/workspace、AST safety check、error classification、structured patch proposal、blocked、verification loop |

**本节小结**：A-D 看似是不同项目，其实都在暴露同一件事：Agent 能力需要 runtime 承载，不能只靠 prompt 和角色设计。

## 八、从项目 E 到独立 Runtime 项目

前面这些讨论最直接的意义，是说明原计划中的项目 E 已经不足以承载当前问题。

原计划里的项目 E 是“评估与安全防线”，并且不是独立项目，而是作为 A-D 的横向基础设施存在。这个定位适合补齐 eval、trace、guardrail 等能力，但不足以系统探索 Agent runtime、Skills、Guardrails、状态、上下文和治理之间的关系。

因此，现在更合理的判断是：

```text
不要把原项目 E 强行扩展成大项目。
应考虑从 E 中拆出一个独立的新项目：Agent Runtime & Governance。
```

这个新项目不应急着做“大而全”的平台，也不应只是给 A-D 补几个零散工具函数。更合适的定位是：

```text
Agent Runtime & Governance 的最小参考实现
```

它的价值不在于一次性做出成熟平台，而在于围绕 Agent runtime/governance 做有边界的实践、探索和研究，沉淀出可迁移的经验和产出。

这个独立项目应重点回答：

- 哪些能力应是所有 Agent 共享的？
- 哪些能力应由业务 Agent 自己实现？
- 如何让 Skills 和 Guardrails 可组合？
- 如何让 trace、eval、safety 成为默认能力？
- 哪些 runtime 能力值得抽象，哪些抽象会过早？
- 如何用小实验验证方法论，而不是直接陷入平台工程？

因此，新的独立项目目标可以设定为：

| 目标 | 说明 |
|------|------|
| 研究 Agent runtime 的最小共性 | 从 A-D 中抽取状态、trace、guardrail、eval、skill 调用等共性能力 |
| 形成可复用判断准则 | 例如什么时候需要状态机，什么时候需要多 Agent，什么时候只需要 skill |
| 做小而完整的参考实现 | 不求通用平台，只做能证明思路的 reference implementation |
| 产出工程经验文档 | 记录哪些抽象有效，哪些过度设计，哪些能力必须前置 |
| 支撑后续项目复用 | 让未来 Agent 项目能复用已有 runtime 思想，而不是从零开始 |

### 为什么不能直接做大平台

从项目 B 到 D-lite 的经验看，Agent 项目的复杂度经常不是来自核心功能，而是来自周边治理：

- 要记录状态，否则无法恢复。
- 要记录 trace，否则无法复盘。
- 要做评估，否则不知道改动是否变好。
- 要做安全检查，否则 prompt 约束不可靠。
- 要做成本控制，否则自主循环很快失控。
- 要做人工介入，否则高风险动作无法上线。

如果这个新项目一开始就做“通用 Agent 平台”，会同时触发所有复杂点，最后容易陷入框架设计而不是学习验证。

更稳妥的路线是三步：

```text
方法论文档
-> 最小 reference implementation
-> 从 A-D 项目中抽取可复用 runtime 能力
```

也就是说，这个独立项目的第一性问题不是“平台有哪些功能”，而是“哪些能力值得从业务 Agent 中抽出来”。

### 独立 Runtime 项目的三种可能形态

| 形态 | 内容 | 优点 | 风险 |
|------|------|------|------|
| 轻量评估与安全库 | eval、guard、trace 的工具函数集合 | 快速落地，风险低 | 容易只是工具箱，不形成 runtime |
| Agent Runtime 最小框架 | 统一状态、trace、guardrail、skill 调用协议 | 抽象能力强 | 容易过度设计 |
| 方法论 + reference implementation | 先写原则，再做小样板验证 | 最适合当前学习阶段 | 短期产品感不强 |

当前推荐第三种：先形成方法论，再用一个很小的 reference implementation 验证。

### 独立 Runtime 项目应产出的东西

为了避免这个项目变成泛泛讨论，它至少应产出以下几类成果：

| 产出 | 价值 |
|------|------|
| Runtime 能力清单 | 明确哪些能力属于公共底座，哪些属于业务 Agent |
| Trace schema 草案 | 统一记录任务、模型、工具、错误、评估和人工介入 |
| Guardrail 分类表 | 区分安全护栏、质量护栏、成本护栏和人工确认 |
| Skill 设计规范 | 定义 Skill 的描述、输入输出、依赖、失败处理和验证方式 |
| 最小参考实现 | 用一个小场景验证 trace、guardrail、skill、eval 的组合方式 |
| 复盘报告 | 总结哪些 runtime 抽象真正有用，哪些暂时不值得工程化 |

**本节小结**：原项目 E 可以保留为 A-D 的横向评估与安全能力，但当前讨论已经超出它的边界。更合理的方向，是把 Agent Runtime & Governance 作为一个新的独立项目候选，用最小实践样板沉淀可复用的判断准则、文档和参考实现。

## 九、设计原则与反模式

### 设计原则

| 原则 | 中文描述 | 含义 |
|------|----------|------|
| Workflow first, agent second | 工作流优先，Agent 其次 | 先确认任务主干和步骤边界，再决定哪里需要 Agent 自主判断 |
| Artifact first, conversation second | 产物优先，对话其次 | 模块之间优先传结构化产物，而不是依赖长对话历史 |
| Verification first, explanation second | 验证优先，解释其次 | Agent 的解释不能代表成功，必须由测试、规则或外部信号验证 |
| Guardrails first, prompt restriction second | 护栏优先，提示词约束其次 | 高风险行为要靠运行时护栏限制，不能只靠 prompt 禁止 |
| Skills first, universal agent second | 技能优先，万能 Agent 其次 | 优先沉淀可复用 Skill，而不是把所有能力塞进一个 Agent |
| Runtime first, demo second | 运行时优先，演示其次 | 真正可用的 Agent 需要状态、trace、权限、恢复和治理能力 |
| Trace first, intuition second | 追踪优先，直觉其次 | 调试和优化应基于可回放 trace，而不是只靠观察最终输出 |
| Evaluation first, optimization second | 评估优先，优化其次 | 没有基线和回归集时，不应频繁调 prompt 或改流程 |

### 反模式清单

- 用多 Agent 掩盖任务边界不清。
- 用 prompt 禁止危险行为，却不给工具权限限制。
- 让 Reviewer 通过代表系统质量稳定。
- 把完整历史对话当作状态。
- 只保存最终结果，不保存中间 artifact。
- 没有 max steps、timeout、budget。
- 让 LLM 直接执行外部写操作。
- 没有 trace，却试图调试 Agent。
- 没有回归集，却频繁调 prompt。
- 把安全拦截图省事地算作失败。

**本节小结**：设计原则用于指导取舍，反模式用于快速识别项目正在失控的信号。

## 十、后续探索问题

这些问题适合作为下一阶段方法论或独立 Runtime 项目的起点：

1. Skill 的最小标准是什么？
2. Guardrail 如何独立于具体 Agent 存在？
3. Trace schema 应该如何统一？
4. Agent 的状态如何兼顾可恢复和隐私/成本？
5. 什么时候应该使用多 Agent，而不是单 Agent + skills？
6. LLM patch 应该使用整文件、replacement 还是 unified diff？
7. LLM-as-a-Judge 在哪些地方可靠，哪些地方必须人类复核？
8. Runtime 如何支持多模型、多 provider 和模型降级？

## 参考资料

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [OpenAI: New tools for building agents](https://openai.com/index/new-tools-for-building-agents/)
- [OpenAI Agents SDK: Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [OpenAI Agents SDK: Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Google: Agents whitepaper](https://storage.ghost.io/c/dc/a8/dca8ae32-7ed6-405a-b948-680b55c8f3dc/content/files/2025/01/Whitepaper-Agents---Google.pdf)
- [LangChain: The runtime behind production deep agents](https://www.langchain.com/blog/runtime-behind-production-deep-agents)
- [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro)
