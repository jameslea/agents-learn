# Agent 核心能力小步验证开发计划

> 更新时间：2026-05-19
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
| 3 | Checkpoint / Resume | pending | 待补充 | 待补充 | 待补充 |
| 4 | Schema Artifact 交接 | pending | 待补充 | 待补充 | 待补充 |
| 5 | Trace 与复盘 | pending | 待补充 | 待补充 | 待补充 |
| 6 | 最小 Runtime 串联 | pending | 待补充 | 待补充 | 待补充 |

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

推荐目录方向：

```text
practice-projects/06-agent-runtime-core/
  runtime_core/
    contracts.py
    state.py
    context.py
    memory.py
    artifact.py
    trace.py
    step_runner.py
  scenarios/
    research_mini/
    code_review_mini/
  scripts/
    run_context_demo.py
    run_resume_demo.py
    run_artifact_handoff_demo.py
    run_trace_demo.py
```

如果旧项目中已有相似能力，只作为参考，不直接耦合。新项目应保持小核心、
低依赖和清晰边界。

核心对象建议保持少量：

| 对象 | 职责 |
|------|------|
| `RuntimeState` | 保存任务状态、当前 step、预算、恢复点 |
| `ContextBundle` | 表示一次模型调用所需上下文 |
| `MemoryRecord` | 表示跨任务可复用信息 |
| `Artifact` | 表示结构化中间产物 |
| `TraceEvent` | 表示一次 step、tool、artifact 或错误事件 |
| `StepRunner` | 串联 step 执行、状态更新、trace 写入 |

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
- trace 中能看到 artifact 生成和消费关系。

## 十、阶段 5：Trace 与复盘验证

目标：验证失败后能复盘，而不是只看到最终失败。

需要记录：

| Trace 事件 | 内容 |
|------------|------|
| step_started | step_id、input summary、time |
| model_called | provider、model、latency、token 可选 |
| tool_called | tool、args summary、risk |
| artifact_created | artifact id、schema、path |
| step_failed | error type、message、recoverable |
| step_passed | output summary、time |
| human_required | reason、risk、pending action |

验收标准：

- 每次 demo 运行生成 trace。
- 失败时能根据 trace 定位 step 和原因。
- trace 不泄露 API key 等敏感内容。

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
| Blocked 终态 | 工具越权、schema 不合格、预算超限、重复失败时进入 `blocked`，输出原因和人工处理建议 |

验收标准：

- 一个命令可运行完整流程。
- 支持中断后恢复。
- 每个 step 有 artifact 或 trace。
- 最终输出包括 report、review result、trace summary。
- 工具策略、预算超限和 blocked 状态至少各有一个可演示样例。

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
| 3 | pending | 2026-05-19 | 尚未开始 |
| 4 | pending | 2026-05-19 | 尚未开始 |
| 5 | pending | 2026-05-19 | 尚未开始 |
| 6 | pending | 2026-05-19 | 尚未开始 |

### 阶段 1：Context Builder

- 状态：completed
- 完成日期：2026-05-19
- 代码根目录：`practice-projects/06-agent-runtime-core/`
- 相对文件：
  - `runtime_core/context.py`
  - `runtime_core/contracts.py`
  - `runtime_core/state.py`
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
  - `runtime_core/memory.py`
  - `runtime_core/artifact.py`
  - `runtime_core/context.py`
  - `runtime_core/state.py`
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
- 后续调整：阶段 3 可以基于 `RuntimeState` 增加 checkpoint / resume；阶段 4 可以继续强化 `ArtifactRecord` 的 schema 验证和交接能力。
- 记忆系统后续增强清单：
  - 持久化 store：与 checkpoint / trace store 统一设计后再做。
  - 冲突和重复检测：记忆样本增多后再补，避免记忆膨胀和规则矛盾。
  - 审计日志：和 trace 阶段一起记录 memory 写入、验证、替换和失效过程。
  - 权限、隔离和敏感信息治理：接入真实多用户或多项目场景时补充。
  - 语义检索和自动记忆抽取：放在后续阶段，且必须经过 write gate 和验证流程。
  - 记忆效果评估：和 eval / trace 体系结合，判断 memory 是否真正提升任务质量。
