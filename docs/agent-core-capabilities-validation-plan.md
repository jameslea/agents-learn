# Agent 核心能力小步验证开发计划

> 更新时间：2026-05-20
>
> 本文用于指导下一阶段 Agent 实践开发。目标不是继续扩大项目范围，也不是一次性实现完整生产级 Runtime，而是围绕前期文档中反复确认的核心能力做小步验证：上下文管理、记忆管理、可恢复、可交接、可复盘，以及最小 Runtime 支撑。每一项都应有可运行脚本、清晰输入输出、可观察 trace 和阶段性复盘。

## 目录

- [一、计划定位](#一计划定位)
- [二、核心原则](#二核心原则)
- [三、计划进度总览](#三计划进度总览)
- [四、目标能力清单](#四目标能力清单)
- [五、总体架构方向](#五总体架构方向)
- [六、阶段 1：Context Builder 最小验证](#六阶段-1context-builder-最小验证)
- [七、阶段 2：Memory 与 State 分层验证](#七阶段-2memory-与-state-分层验证)
- [八、阶段 3：Checkpoint / Resume 最小验证](#八阶段-3checkpoint--resume-最小验证)
- [九、阶段 4：Schema Artifact 交接验证](#九阶段-4schema-artifact-交接验证)
- [十、阶段 5：Trace 与复盘验证](#十阶段-5trace-与复盘验证)
- [十一、阶段 6：最小 Runtime 串联验证](#十一阶段-6最小-runtime-串联验证)
- [十二、验收标准](#十二验收标准)
- [十三、暂不做的事情](#十三暂不做的事情)
- [十四、推荐推进顺序](#十四推荐推进顺序)
- [十五、进展记录与经验教训](#十五进展记录与经验教训)

## 一、计划定位

前期文档已经基本确立了 Agent 开发的核心范畴：

```text
Model + Tools + Orchestration
  + Context / State / Memory
  + Artifact / Trace
  + Guardrails / Evaluation / Runtime
```

这些内容很大，不能一次性做完。下一阶段更合适的目标是：选几个最关键、最容易在真实 Agent 中反复复用的能力，分别做小型、可运行、可验证的实验。

本文承接以下文档：

- `docs/concepts/agent-core-structure.md`：Agent 核心结构。
- `docs/concepts/agent-theory-to-practice.md`：理论到实践中的问题、失败模式与工程应对。
- `docs/concepts/agent-runtime-philosophy.md`：哪些能力应沉淀为 Runtime。
- `docs/concepts/agent-system-boundaries.md`：生产级 Agent 的工程边界。

本文不是替代旧的 `docs/practice-projects-plan.md`。旧计划关注 A-E 场景项目；本文关注跨 Agent 的公共能力验证。

## 二、核心原则

下一阶段开发遵循下面原则：

| 原则 | 说明 |
|------|------|
| 小步验证 | 每个能力单独验证，不一次性做大框架 |
| 可运行 | 每个阶段都要有可执行脚本或命令 |
| 可观察 | 每次运行都能看到 state、artifact、trace 的变化 |
| 可复盘 | 失败时能知道是哪一步、哪个输入、哪个工具导致 |
| 不追求通用 | 先服务 1-2 个具体 Agent 场景，再考虑抽象 |
| 不依赖多 Agent | 优先验证单 Agent 的基础能力，多 Agent 后置 |
| 不急于产品化 | 先沉淀工程判断，再考虑 UI、插件市场、部署系统 |

核心目标可以概括为：

```text
不是再做一个 Agent demo，
而是验证 Agent 能否被更可靠地运行、交接、恢复和复盘。
```

## 三、计划进度总览

状态说明：

| 状态 | 含义 |
|------|------|
| pending | 尚未开始 |
| in_progress | 正在实现或验证 |
| completed | 已完成实现、验证和复盘记录 |
| blocked | 因依赖、设计或环境问题暂停 |
| deferred | 有价值但本阶段暂缓 |

当前进度：

| 阶段 | 能力 | 状态 | 产出 | 验证 | 记录 |
|------|------|------|------|------|------|
| 1 | Context Builder | completed | 见阶段 1 明细 | 见阶段 1 明细 | 已记录核心概念和经验教训 |
| 2 | Memory / State 分层 | completed | 见阶段 2 明细 | 见阶段 2 明细 | 已记录核心概念和经验教训 |
| 3 | Checkpoint / Resume | completed | 见阶段 3 明细 | 见阶段 3 明细 | 已记录核心概念和经验教训 |
| 4 | Schema Artifact 交接 | completed | 见阶段 4 明细 | 见阶段 4 明细 | 已记录核心概念和经验教训 |
| 5 | Trace 与复盘 | completed | 见阶段 5 明细 | 见阶段 5 明细 | 已记录核心概念和经验教训 |
| 6 | 最小 Runtime 串联 | completed | 见阶段 6 明细 | 见阶段 6 明细 | 已记录核心概念和经验教训 |
| 7 | code_review_mini 场景试验 | completed | 见阶段 7 明细 | 见阶段 7 明细 | 已记录核心概念和经验教训 |

维护要求：

- 每开始一个阶段，将状态改为 `in_progress`。
- 每完成一个阶段，将状态改为 `completed`，并在阶段明细中补充代码根目录、相对文件、验证命令、核心概念记录和经验教训记录。
- 如果阶段被卡住，将状态改为 `blocked`，说明阻塞原因和下一步处理方式。
- 不允许只提交代码而不更新本计划状态。
- 每个阶段至少记录 1-3 条核心概念和 1-3 条经验教训。

## 四、目标能力清单

| 能力 | 要验证的问题 | 最小产物 |
|------|--------------|----------|
| Context Builder | 当前 step 需要哪些信息，如何避免上下文膨胀和污染 | 可打印的 context bundle |
| Memory / State 分层 | 什么是长期记忆，什么是任务状态，什么是 artifact | 三类数据模型和样例 |
| Checkpoint / Resume | 长任务中断后是否能恢复，而不是重跑 | 可恢复的 step runner |
| Schema Artifact | Agent 之间是否能通过结构化产物交接 | Pydantic artifact + validator |
| Trace | 失败后是否能复盘输入、工具、输出、错误 | JSONL trace 或 SQLite trace |
| Tool Policy | 工具权限、风险等级和副作用如何控制 | 最小工具策略表和调用前检查 |
| Budget / Latency | 成本、延迟、调用次数如何观测和限制 | step 级预算和耗时记录 |
| Blocked 终态 | 失败如何停下来，而不是无限循环 | blocked 状态、原因和人工介入提示 |
| Runtime 串联 | 上述能力是否能支撑一个最小真实 Agent 流程 | 一个端到端 mini agent |

覆盖关系如下：

| 关注问题 | 本计划中的覆盖位置 | 覆盖方式 |
|----------|--------------------|----------|
| 上下文怎么选 | 阶段 1：Context Builder | 按目标、step、artifact、memory 和 trace summary 构造 `ContextBundle` |
| 上下文怎么压缩 | 阶段 1：Context Builder | 最近 step 摘要、artifact 引用、trace 摘要，不直接塞完整历史 |
| 上下文怎么防污染 | 阶段 1、阶段 2 | 只选择相关 memory / artifact，并区分有效状态、过期记忆和原始 trace |
| 记忆怎么保存 | 阶段 2：Memory / State 分层 | 使用 `MemoryRecord`，和 `RuntimeState`、`ArtifactRecord` 分开保存 |
| 记忆怎么验证 | 阶段 2、阶段 6 | 给 memory 增加来源、scope、tag、confidence 和验证状态 |
| 记忆怎么过期 | 阶段 2 | 给 memory 增加时间、版本、有效范围和失效规则 |
| 状态怎么 checkpoint / resume | 阶段 3 | step 状态、checkpoint 文件或 SQLite、resume 脚本 |
| Agent 怎么通过 artifact 交接 | 阶段 4 | `EvidenceTable`、`DraftReport`、`ReviewResult` 等 schema artifact |
| trace 怎么足以复盘但不过载 | 阶段 5 | 记录关键事件和摘要，避免保存敏感信息和完整上下文原文 |
| 工具权限怎么控制 | 阶段 5、阶段 6 横向要求 | 记录 tool risk，增加最小 `ToolPolicy` 和调用前检查 |
| 成本和延迟怎么治理 | 阶段 5、阶段 6 横向要求 | 记录 provider、model、latency、调用次数和 step budget |
| 失败如何进入 blocked | 阶段 3、阶段 6 横向要求 | step 状态包含 `blocked`，记录 blocked reason 和可恢复建议 |
| Runtime 如何保持小核心 | 阶段 6、暂不做的事情 | 只串联 state、context、memory、artifact、trace、step runner，不做插件市场和大框架 |

## 五、总体架构方向

本计划后续开发应放在独立的新项目目录中进行，不再继续叠加到旧的项目 E
`practice-projects/05-agent-runtime-governance`。旧项目保留为 Runtime & Governance
探索阶段的历史样本，新项目用于干净地验证 Runtime Core 公共能力。

当前代码根目录：

```text
practice-projects/06-agent-runtime-core/
```

阶段明细中的文件路径默认相对于该代码根目录记录，避免进度表被长路径撑开。

本计划的阶段划分和代码目录划分采用不同维度：

- 阶段文档按能力验证顺序组织，用来记录目标、验证方式、阶段产出和经验教训。
- 代码目录按 Runtime 领域职责组织，用来保持公共模块边界清晰。

因此二者不是一一对应关系。一个阶段可能涉及多个代码包，一个代码包也可能被多个阶段复用。

推荐目录方向：

```text
practice-projects/06-agent-runtime-core/
  runtime_core/
    context/
    memory/
    artifact/
    task/
    execution/
    observability/
  scenarios/
    research_mini/
      schemas.py
      scenario.py
    code_review_mini/
  scripts/
    run_context_demo.py
    run_resume_demo.py
    run_artifact_handoff_demo.py
    run_trace_demo.py
```

如果旧项目中已有相似能力，只作为参考，不直接耦合。新项目应保持小核心、
低依赖和清晰边界。

阶段与代码包的大致映射如下：

| 阶段 | 主要代码包 | 说明 |
|------|------------|------|
| 阶段 1：Context Builder | `task/`、`context/` | 任务契约、状态摘要和上下文构造 |
| 阶段 2：Memory / State 分层 | `memory/`、`task/`、`artifact/`、`context/` | 记忆、状态和 artifact 边界 |
| 阶段 3：Checkpoint / Resume | `observability/checkpoint/`、`execution/`、`task/` | checkpoint、step runner 和恢复语义 |
| 阶段 4：Schema Artifact 交接 | `artifact/`、`scenarios/research_mini/schemas.py` | Runtime 提供 artifact 记录和 store，具体 schema 属于场景 |
| 阶段 5：Trace 与复盘 | `observability/trace/` | JSONL trace、读取、复盘和脱敏 |
| 阶段 6：最小 Runtime 串联 | `execution/`、`scenarios/research_mini/` | 最小 Runtime 串联和具体业务场景 |
| 阶段 7：code_review_mini 场景试验 | `scenarios/code_review_mini/`、`execution/`、`artifact/`、`observability/` | 用具体代码审查场景验证 Runtime Core public API |

核心对象建议保持少量：

| 对象 | 职责 |
|------|------|
| `RuntimeState` | 保存任务状态、当前 step、预算、恢复点 |
| `ContextBundle` | 表示一次模型调用所需上下文 |
| `MemoryRecord` | 表示跨任务可复用信息 |
| `ArtifactRecord` | 表示结构化中间产物 |
| `TraceEvent` | 表示一次 step、tool、artifact 或错误事件 |
| `StepRunner` | 串联 step 执行、状态更新、checkpoint 保存和 resume |

## 六、阶段 1：Context Builder 最小验证

目标：验证上下文不是聊天历史，而是当前 step 的工作视图。

最小场景：

```text
给定一个任务目标、若干历史 step、若干 artifact、若干 memory，
构造当前 step 的 ContextBundle。
```

需要实现：

- `ContextBundle` 数据结构。
- `ContextBuilder`。
- 简单的上下文选择规则。
- demo 脚本输出最终 context。

建议规则：

| 信息类型 | 进入 context 的条件 |
|----------|---------------------|
| 当前目标 | 总是进入 |
| 当前 step | 总是进入 |
| 最近 step 摘要 | 只保留最近 N 条 |
| artifact | 只引用和当前 step 相关的 |
| memory | 按 scope 和 tag 选择 |
| trace 原文 | 默认不进入，只进入摘要 |

验收标准：

- 能打印出结构化 context bundle。
- 能解释为什么某条 memory / artifact 被选中或被排除。
- 上下文中不直接塞完整历史 trace。

## 七、阶段 2：Memory 与 State 分层验证

目标：验证长期记忆、任务状态和 artifact 不是同一个东西。

需要实现或整理：

- `RuntimeState`：当前任务进度。
- `MemoryRecord`：跨任务经验。
- `ArtifactRecord`：任务内或跨任务可引用产物。

样例数据：

| 类型 | 示例 |
|------|------|
| State | 当前任务执行到 `draft_report`，已完成 `collect_sources` |
| Memory | 用户偏好 Markdown 输出；项目使用 MiniMax 作为调试模型 |
| Artifact | `research_plan.json`、`evidence_table.json`、`review_result.json` |

验收标准：

- 三类数据能分别创建、读取和传递。本阶段不实现持久化 store。
- context builder 能按需引用它们。
- 文档中说明三者边界，避免混用。

## 八、阶段 3：Checkpoint / Resume 最小验证

目标：验证长任务中断后可以恢复到明确 step，而不是从头重跑。

最小场景：

```text
一个三步任务：
1. collect
2. summarize
3. review

在第 2 步后模拟中断。
再次运行时从第 3 步恢复。
```

需要实现：

- step 状态：pending、running、passed、failed、blocked、skipped。
- checkpoint 文件或 SQLite 记录。
- resume 脚本。
- 重复运行时不重复已完成 step。

验收标准：

- 第一次运行可以在指定 step 后中断。
- 第二次运行能从 checkpoint 恢复。
- trace 中能看到恢复过程。

## 九、阶段 4：Schema Artifact 交接验证

目标：验证 Agent 或 step 之间通过结构化 artifact 交接，而不是自由文本。

最小场景：

```text
Research Step -> EvidenceTable artifact
Writer Step -> 读取 EvidenceTable 生成 DraftReport
Reviewer Step -> 读取 DraftReport 生成 ReviewResult
```

需要实现：

- 2-3 个 Pydantic artifact schema。
- artifact validator。
- artifact store。
- handoff demo。

建议 artifact：

| Artifact | 字段示例 |
|----------|----------|
| `EvidenceTable` | claim、source、confidence、notes |
| `DraftReport` | title、sections、evidence_refs |
| `ReviewResult` | score、issues、required_changes、passed |

验收标准：

- 下游 step 不读取上游自由文本，而读取 artifact。
- artifact 缺字段或不合格时能失败并记录原因。
- artifact metadata 中能看到生成和消费关系；正式 trace 记录放到阶段 5。

## 十、阶段 5：Trace 与复盘验证

目标：验证失败后能复盘，而不是只看到最终失败。

需要记录：

| Trace 事件 | 内容 |
|------------|------|
| task_started | task_id、task_type、goal summary |
| task_finished | final status、summary |
| step_started | step_id、input summary、time |
| tool_called | tool、args summary、risk |
| artifact_created | artifact id、schema、path |
| artifact_consumed | artifact id、schema、consumer step |
| step_failed | error type、message、recoverable |
| step_passed | output summary、time |
| human_required | reason、risk、pending action |

验收标准：

- 每次 demo 运行生成 trace。
- 失败时能根据 trace 定位 step 和原因。
- trace 不泄露 API key 等敏感内容。
- trace 中记录 artifact 引用，而不是完整 artifact payload。

## 十一、阶段 6：最小 Runtime 串联验证

目标：把前面能力串起来，形成一个最小真实 Agent 场景。

推荐优先场景：

```text
research_mini：
给定一个主题，
生成 research plan，
整理 evidence table，
生成短报告，
评审并输出 review result。
```

这个场景比 D-lite 安全，且能覆盖：

- context builder。
- memory / state。
- checkpoint / resume。
- artifact handoff。
- trace。
- 简单 evaluation。

同时加入三条横向治理约束：

| 约束 | 最小实现 |
|------|----------|
| Tool Policy | 每个工具声明 `risk_level`、`read_only`、`requires_approval`，调用前做检查 |
| Budget / Latency | 每个 step 记录开始时间、结束时间、模型调用次数和可选 token / cost |
| Blocked 终态 | 工具越权、schema 不合格或重复失败时进入 `blocked`，输出原因和人工处理建议 |

验收标准：

- 一个命令可运行完整流程。
- 支持中断后恢复。
- 每个 step 有 artifact 或 trace。
- 最终输出包括 report、review result、trace summary。
- 工具策略和 blocked 状态至少各有一个可演示样例。
- 预算和延迟先通过 step 时间与 trace 观察，不在本阶段实现完整成本系统。

## 十二、验收标准

阶段性完成不以“Agent 多聪明”为标准，而以工程能力是否可观察、可恢复、可复盘为标准。

| 维度 | 验收问题 |
|------|----------|
| 可运行 | 是否有明确命令可以执行 demo |
| 可恢复 | 中断后是否能 resume |
| 可交接 | 下游是否消费 schema artifact |
| 可复盘 | trace 是否能定位失败原因 |
| 可解释 | context builder 是否能说明选择了哪些信息 |
| 可扩展 | 新场景是否能复用核心对象，而不是复制代码 |
| 有边界 | 是否明确哪些能力暂不做 |

## 十三、暂不做的事情

为了避免再次变成过大的 Runtime 项目，下一阶段暂不做：

- 不做通用插件市场。
- 不做完整 Web UI。
- 不做多租户、权限后台和企业部署。
- 不做复杂多模态。
- 不做复杂自动评测平台。
- 不做跨语言 SDK。
- 不追求支持所有 Agent 项目。

这些都属于后续工程化增强。当前阶段只验证核心能力是否成立。

## 十四、推荐推进顺序

建议顺序：

1. 先实现 `ContextBundle` 和 `ContextBuilder`。
2. 再明确 `RuntimeState`、`MemoryRecord`、`ArtifactRecord` 的边界。
3. 增加 checkpoint / resume。
4. 增加 schema artifact handoff。
5. 增加 trace event 和 trace summary。
6. 最后串成 `research_mini` 或其他最小场景。

每完成一个阶段，都应补充：

- 运行命令。
- 示例输出。
- 遇到的问题。
- 当前设计边界。
- 下一步是否需要调整。

这份计划的最终目标不是产出“完整 Agent Runtime”，而是让后续 Agent 开发逐步具备：

```text
可控上下文，
清晰状态，
结构化交接，
可恢复执行，
可复盘 trace，
最小公共 Runtime。
```

## 十五、进展记录与经验教训

每完成一个阶段，应在本节补充记录。记录不追求长，但必须能帮助后续开发回看当时的判断、产物和问题。

记录模板：

```markdown
### 阶段 N：阶段名称

- 状态：completed / blocked / deferred
- 完成日期：YYYY-MM-DD
- 代码根目录：
- 相对文件：
- 验证命令：
- 关键产物：
- 核心概念：
  - 概念 1：
  - 概念 2：
- 经验教训：
  - 经验 1：
  - 经验 2：
- 后续调整：
```

当前记录：

| 阶段 | 状态 | 最近更新 | 记录 |
|------|------|----------|------|
| 1 | completed | 2026-05-19 | 已完成 Context Builder 最小验证，新增结构化 `ContextBundle`、候选筛选规则、demo 和测试 |
| 2 | completed | 2026-05-19 | 已完成 Memory / State 分层和轻量记忆机制验证，新增 `MemoryRecord`、`MemoryWriteGate`、`MemoryStore`、`ArtifactRecord`、demo 和边界测试 |
| 3 | completed | 2026-05-20 | 已完成 Checkpoint / Resume 最小验证，新增本地 JSON checkpoint、顺序 StepRunner、resume demo 和测试 |
| 4 | completed | 2026-05-20 | 已完成 Schema Artifact 交接最小验证，新增 schema artifact、内存版 ArtifactStore、handoff demo 和测试 |
| 5 | completed | 2026-05-20 | 已完成 Trace 与复盘最小验证，新增 JSONL trace recorder、reader、replay summary、trace demo 和测试 |
| 6 | completed | 2026-05-20 | 已完成最小 Runtime 串联验证，新增 MinimalRuntime、ToolPolicyChecker、research_mini 场景、端到端 demo 和测试 |
| 7 | completed | 2026-05-20 | 已完成 code_review_mini 场景试验，新增真实 LLM 可选 reviewer、schema artifact、blocked 演示、resume 演示和测试 |

### 阶段 1：Context Builder

- 状态：completed
- 完成日期：2026-05-19
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/context/`
  - `runtime_core/task/`
  - `scripts/run_context_demo.py`
  - `tests/test_context_builder.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_context_demo.py`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`ContextBundle`、`ContextBuilder`、`ContextSelection`、`ContextPolicy`、`ContextCandidate`、`ContextMetrics`、`ArtifactCandidate`、`MemoryCandidate`。
- 核心概念：
  - Context 是当前 step 的工作视图，不是完整聊天历史或完整 trace。
  - Context Builder 应同时输出上下文内容和选择日志，让上下文来源可解释。
  - Artifact 默认进入引用、摘要和路径，memory 需要经过 scope、tag、置信度、有效期和验证状态筛选。
  - 上下文选择应由策略控制，并区分可见性、信任等级、敏感候选和 required context。
- 经验教训：
  - 先用确定性规则可以更清楚地观察上下文污染、上下文膨胀和信息遗漏问题。
  - selection log 很重要，否则只能看到最终上下文，无法判断信息为什么进入或被排除。
  - Context metrics 可以让上下文工程从“看最终 prompt”变成“观察选择过程和预算使用”。
  - Stage 1 暂不实现向量检索、LLM 压缩和长期 memory store，避免第一步过度复杂化。
  - Python 项目不必机械采用 Java 式“一类一文件”，但也不应把 enum、model、policy、selector、budget、builder 都长期堆在一个模块中；更合理的粒度是按概念职责拆分，例如 source、candidate、policy、selection、output、budget、builder。
- 后续调整：阶段 2 已把当前临时 `MemoryCandidate` 演进为独立 `MemoryRecord`，并进一步区分 project memory、task state 和 artifact。

### 阶段 2：Memory / State 分层

- 状态：completed
- 完成日期：2026-05-19
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/memory/`
  - `runtime_core/artifact/`
  - `runtime_core/context/`
  - `runtime_core/task/`
  - `scripts/run_memory_state_demo.py`
  - `tests/test_memory_state_boundaries.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_memory_state_demo.py`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`MemoryRecord`、`MemoryWriteProposal`、`MemoryWriteGate`、`MemoryWriteDecision`、内存版 `MemoryStore`、`MemoryQuery`、`MemorySearchResult`、`ArtifactRecord`、`RuntimeState` 边界说明、正式记录接入 Context Builder。
- 核心概念：
  - Memory 是跨任务可复用经验，不是当前任务执行状态。
  - 记忆写入必须经过 gate，先判断复用价值、来源可信度、敏感性、tags、evidence 和 confidence。
  - MemoryStore 管理记忆生命周期，至少应覆盖提出、验证、检索、失效和替换；当前实现是进程内内存 store，不做持久化。
  - State 是当前任务执行进度，只保存 step、短摘要、artifact id 引用和少量 runtime values。
  - Artifact 是可验证、可交接的结构化产物，Context Builder 默认只引用 summary / path / schema。
  - Context Builder 可以接入正式 `MemoryRecord` 和 `ArtifactRecord`，但仍通过候选转换和选择规则治理。
- 经验教训：
  - 先划清边界，再补轻量 memory store，比直接做复杂记忆系统更稳。
  - 记忆写入时机不能缺失；没有 write gate 时，Agent 容易把临时状态、错误推断或外部污染写成长久记忆。
  - MemoryStore 应先完成记忆写入、验证、检索排序、失效和替换，再把结果交给 Context Builder；持久化可以后续替换 store 实现，不应污染 `MemoryRecord` 边界。
  - Artifact 可以有完整 payload，但上下文中默认不读取 payload，避免上下文膨胀。
  - Memory 即使是正式记录，也必须保留 validated、confidence、expires_at、scope、tags 等治理元数据。
  - 保留 `MemoryCandidate` 和 `ArtifactCandidate` 有助于兼容阶段 1，但后续应逐步将正式模型作为主入口。
- 后续调整：阶段 3 已基于 `RuntimeState` 增加 checkpoint / resume；阶段 4 已继续强化 `ArtifactRecord` 的 schema 验证和交接能力。
- 记忆系统后续增强清单：
  - 持久化 store：与 checkpoint / trace store 统一设计后再做。
  - 冲突和重复检测：记忆样本增多后再补，避免记忆膨胀和规则矛盾。
  - 审计日志：和 trace 阶段一起记录 memory 写入、验证、替换和失效过程。
  - 权限、隔离和敏感信息治理：接入真实多用户或多项目场景时补充。
  - 语义检索和自动记忆抽取：放在后续阶段，且必须经过 write gate 和验证流程。
  - 记忆效果评估：和 eval / trace 体系结合，判断 memory 是否真正提升任务质量。

### 阶段 3：Checkpoint / Resume

- 状态：completed
- 完成日期：2026-05-20
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/observability/checkpoint/`
  - `runtime_core/execution/step_runner.py`
  - `runtime_core/task/`
  - `scripts/run_resume_demo.py`
  - `tests/test_checkpoint_resume.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_resume_demo.py`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`CheckpointRecord`、`FileCheckpointStore`、`StepDefinition`、`StepRunner`、`StepRunReport`。
- 核心概念：
  - Checkpoint 保存的是 `RuntimeState` 快照，不是 memory、artifact payload 或完整 trace。
  - Resume 应从 checkpoint 判断已完成 step，而不是人工猜测中断位置。
  - 已完成 step 恢复时不重复执行，并显式记录为 `SKIPPED`，方便复盘。
  - 每个 step 成功后保存 checkpoint，可以降低长任务中断后的重跑成本。
- 经验教训：
  - 最小顺序 StepRunner 足以验证恢复语义，不必一开始就做 DAG 调度。
  - 本地 JSON checkpoint 适合学习和单进程验证，但不适合并发、分布式或事务型恢复。
  - `SKIPPED` 记录很重要，否则恢复后只能看到最终状态，无法解释哪些 step 被跳过。
  - 后续接入真实工具调用后，需要补充 RUNNING step 的恢复策略、retry 和 blocked 状态。
- 后续调整：阶段 4 已基于 `ArtifactRecord` 做 schema artifact 交接；阶段 5 再把 checkpoint / resume 过程写入 trace。

### 阶段 4：Schema Artifact 交接

- 状态：completed
- 完成日期：2026-05-20
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/artifact/`
  - `scenarios/research_mini/schemas.py`
  - `runtime_core/artifact/store.py`
  - `scripts/run_artifact_handoff_demo.py`
  - `tests/test_schema_artifact.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_artifact_handoff_demo.py`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`EvidenceTable`、`DraftReport`、`ReviewResult`、`ArtifactStore`、`ArtifactValidationResult`、`ArtifactValidationError`。
- 核心概念：
  - Artifact 是 step 之间的结构化接口，不只是上下文中的一段文字。
  - `summary` 用于上下文引用，`payload` 用于结构化消费，两者不能混用。
  - 下游 step 通过 `artifact_id + schema_name` 读取 payload，schema name 是消费契约。
  - `ArtifactRecord.validated` 默认不应假定为真，只有经过 schema 或人工校验后才允许下游消费。
  - artifact 保存前和消费时都需要校验，防止缺字段、schema 错配或未验证产物继续传播。
  - 当前通过 `metadata.consumed_artifact_ids` 记录消费关系，正式 trace 放到阶段 5。
- 经验教训：
  - 只有 `ArtifactRecord` 不足以完成可靠交接；没有 schema 校验时，下游仍然要猜字段。
  - 下游消费时也要做 schema 检查，不能只相信上游保存时的状态。
  - 先做内存版 `ArtifactStore` 更适合小步验证；持久化应等 artifact、checkpoint 和 trace 的存储边界更清晰后统一考虑。
  - Context Builder 继续只引用 artifact summary / path / schema，不读取完整 payload，可以避免上下文膨胀。
- 后续调整：阶段 5 应把 artifact created / consumed / validation failed 事件写入 trace，并和 state、checkpoint 关联。

### 阶段 5：Trace 与复盘

- 状态：completed
- 完成日期：2026-05-20
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/observability/trace/`
  - `scripts/run_trace_demo.py`
  - `tests/test_trace_replay.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_trace_demo.py`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`TraceEventType`、`TraceEvent`、`TraceRecorder`、`TraceReader`、`TraceReplaySummary`。
- 核心概念：
  - Trace 记录 runtime 关键事件，不是完整日志、完整上下文或完整 artifact payload。
  - 每条事件都应关联 `task_id`，必要时关联 `step_id`，这样失败后能定位到具体步骤。
  - artifact 进入 trace 时只记录 id、schema、path 和消费关系，不记录完整 payload。
  - tool call 进入 trace 时记录工具名、参数摘要和风险等级，并在写入前脱敏。
  - 失败事件需要包含 `recoverable`，方便后续决定 retry、blocked 或 human required。
- 经验教训：
  - 没有 trace 时，失败后只能看到最终错误；有事件链后，可以定位到 step、artifact 和工具层面。
  - trace 太细会变成噪声和泄露风险，太粗又无法复盘；当前先记录关键事件和摘要。
  - 脱敏应该发生在写入前，而不是读出后，否则敏感信息已经落盘。
  - 阶段 5 先显式记录 trace，不强行侵入 `StepRunner` 和 `ArtifactStore`；阶段 6 再统一串联更稳。
- 后续调整：阶段 6 应把 state、context、artifact、checkpoint 和 trace 通过最小 Runtime 串起来，并逐步减少 demo 中的手工记录。

### 阶段 6：最小 Runtime 串联

- 状态：completed
- 完成日期：2026-05-20
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/execution/minimal_runtime.py`
  - `runtime_core/execution/tool_policy.py`
  - `runtime_core/task/`
  - `scenarios/research_mini/scenario.py`
  - `scripts/run_research_mini.py`
  - `tests/test_minimal_runtime.py`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --stop-after collect_evidence`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --force-blocked`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`MinimalRuntime`、`BlockedReason`、`ToolPolicy`、`ToolPolicyChecker`、`ResearchMiniRunResult`、`research_mini` 场景。
- 核心概念：
  - Runtime Core 应提供公共支撑能力，不应吞掉场景业务逻辑。
  - 具体 Agent 场景通过 contract、state、context、memory、artifact、trace 和 checkpoint 与 Runtime 交互。
  - 命令级 resume 不只需要 `RuntimeState`，还需要恢复下游 step 所需的 artifact 引用或快照。
  - blocked 是一种有意义的终态，不是异常崩溃；它应该包含人能处理的原因和建议。
  - 工具策略可以先从风险等级、只读约束和审批要求做起，不必一开始做完整权限系统。
- 经验教训：
  - 前五个能力单独成立，不等于自然能串起来；真正串联时会暴露 artifact 持久化、运行目录隔离和状态恢复边界。
  - Runtime 保持薄封装更容易理解。业务 step 放在 scenario 中，Runtime 只负责公共能力。
  - JSONL trace 适合本地复盘，但真实运行后可以增加 Langfuse 等可选 backend。
  - 并行 demo 共享同一个 workdir 会污染 trace 和 checkpoint；真实 Runtime 需要明确 run id 或隔离目录。
  - 预算和延迟治理当前只通过 step 时间和 trace 观察，尚未形成完整预算系统。
- 后续调整：可以把 JSONL trace 扩展为多 backend，增加 Langfuse sink；也可以将 artifact snapshot 演进为正式持久化 artifact store。

### 阶段 7：code_review_mini 场景试验

- 状态：completed
- 完成日期：2026-05-20
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `scenarios/code_review_mini/`
  - `scripts/run_code_review_mini.py`
  - `tests/test_code_review_mini.py`
  - `docs/07-code-review-mini.md`
- 验证命令：
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --stop-after llm_or_rule_review`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py`
  - `python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --force-blocked`
  - `python3 -m pytest practice-projects/06-agent-runtime-core/tests`
- 关键产物：`CodeSnapshot`、`CodeFinding`、`ReviewReport`、`PatchSuggestion`、`CodeReviewLLMReviewer`、`CodeReviewMiniRunResult`。
- 核心概念：
  - Runtime Core 的优化应由具体场景驱动，而不是预先建设生产级框架能力。
  - 真实 LLM reviewer 属于场景能力，Runtime Core 只负责承载 artifact、trace、checkpoint、blocked 等公共机制。
  - Patch suggestion 是结构化产物，不应等同于直接修改文件。
  - Tool policy 可以判断风险和审批要求，但 blocked / preview / 继续执行的业务取舍仍由场景决定。
- 经验教训：
  - `MinimalRuntime` 可以支持非 research 场景，说明当前 public API 有一定可复用性。
  - LLM 调用需要场景侧包装和 schema 校验，暂时不应抽成通用 LLM step adapter。
  - 代码审查场景暴露出多文件、并行检查、测试执行和补丁应用等潜在需求，但这些都应继续留在后续场景验证中，不急着进入 core。
  - 离线 reviewer 对测试稳定性有价值，真实 LLM 用 `--llm` 显式开启更适合当前阶段。
- 后续调整：继续用新场景记录 Runtime Core 使用摩擦；当两个以上场景反复需要同一能力时，再考虑抽回 core。
