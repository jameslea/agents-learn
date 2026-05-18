# Agent Runtime & Governance Lab 开发计划

> 更新时间：2026-05-18
>
> 本文是后续 Agent 探索与实践的新推进计划。它承接 A/B/C/D-lite 的实践结果，以及 `docs/concepts` 中关于 Agent 设计方法论、Runtime 哲学、框架服务选型和多模态能力的讨论。

## 1. 背景与重新定位

前面的实践已经说明：继续堆更多 Agent demo 的边际收益在下降。

已有项目分别暴露了不同问题：

| 项目 | 已获得的经验 | 暴露的问题 |
|------|--------------|------------|
| A：知识库问答 | RAG 需要检索质量、reranker 和忠实度控制 | 缺少统一评估、trace 和检索失败诊断 |
| B：内容创作团队 | 多角色协作需要结构化产物和评审标准 | 角色多不等于质量稳定，容易 prompt 接龙 |
| C：自主调研助手 | 长任务需要任务队列、反思、成本控制和 checkpoint | 目标漂移、上下文膨胀、停止条件仍是核心风险 |
| D-lite：自愈最小实验 | 自愈 Agent 必须有安全边界、客观验证和 trace | 修复能力必须绑定测试、权限和 blocked 终态 |

这些经验共同指向一个结论：

```text
下一阶段最有价值的目标，不是再证明 Agent 能做什么，
而是验证如何让 Agent 可控、可评估、可复盘、可组合地做事。
```

因此，原计划中的项目 E 不再只是“评估与安全防线”的横向附属模块，而应升级为一个独立的实践主线：

```text
Agent Runtime & Governance Lab
```

## 2. 项目目标

本项目的目标是实现一个最小但完整的 Agent Runtime & Governance 参考实践。

它不追求成为通用框架，也不追求覆盖所有场景，而是围绕已有 A/B/C/D-lite 实践，抽取出可复用的运行时能力。更准确地说，Runtime 应作为不同 Agent 项目的公共运行环境和治理底座。

核心目标：

1. 定义统一的任务契约，明确输入、输出、成功标准、风险等级和预算。
2. 定义 AgentAdapter 接入协议，让不同范式的 Agent 项目可以接入同一个 Runtime。
3. 定义统一的结构化产物协议，让 Agent 之间不再依赖长对话交接。
4. 定义统一的 trace 记录格式，让每一步模型调用、工具调用、验证和失败都可回放。
5. 定义工具治理机制，管理工具权限、参数、审批、blocked 终态和风险等级。
6. 定义运行结果观测与验证机制，把 evaluation 作为 Runtime 的配套能力，而不是项目目标本身。
7. 定义 human-in-the-loop 机制，让高风险节点进入人工确认。
8. 以小模型和多模态能力作为可选扩展，验证“多种有限能力如何组成可靠系统”。

## 3. 非目标

为了避免复杂度失控，本项目明确不做：

- 不做通用 Agent 框架产品。
- 不做完整低代码平台。
- 不做 Dify、Coze、LangGraph、AutoGen、CrewAI 的横向评测项目。
- 不做 Kubernetes、SSH、CI、云厂商运维适配。
- 不做完整多模态产品或实时语音 Agent 产品。
- 不把所有已有项目重写成同一个框架。
- 不追求“万能 Agent”，只研究 runtime 如何约束和组织有限能力。

## 4. 总体架构

最小运行时结构：

```text
TaskContract
  -> RuntimeState
  -> StepExecution
  -> Skill / Tool Invocation
  -> Artifact
  -> ArtifactStore
  -> RunLock
  -> Validator
  -> TraceEvent
  -> EvaluationResult
  -> FinalReport
```

核心思想：

- `TaskContract` 描述要做什么、怎么判断成功、允许使用什么能力。
- `AgentAdapter` 描述一个具体 Agent 项目如何进入 Runtime 生命周期。
- `RuntimeState` 描述任务当前阶段、预算、已产物、状态值、失败和恢复点。
- `StepExecution` 描述一次可追踪的执行步骤，让 Runtime 不是一次函数调用，而是可治理的任务过程。
- `RuntimeCheckpointStore` 在关键生命周期节点保存状态，先支撑失败复盘，后续再支撑 resume。
- `Skill / Tool Invocation` 描述一次受治理的能力调用。
- `Artifact` 描述稳定产物，而不是自由文本。
- `ArtifactStore` 保存大段中间产物和最终产物，RuntimeState 和 trace 只保存引用。
- `RunLock` 阻止同一个 adapter 并发写入同一组 trace、checkpoint 和 artifact。
- `run_id` 将一次具名运行的 trace、checkpoint、artifact、lock 和场景输出隔离到独立路径。
- `Validator` 做结构校验、规则校验或客观测试。
- `TraceEvent` 记录过程，让失败可以复盘。
- `EvaluationResult` 记录质量、安全、成本和延迟。
- `FinalReport` 汇总证据，而不是只给自然语言结论。

## 5. 核心模块

### 5.1 Task Contract

定义任务入口协议。

建议字段：

| 字段 | 说明 |
|------|------|
| `task_id` | 任务唯一标识 |
| `task_type` | 任务类型，如 `rag_qa`、`research`、`self_heal`、`multimodal_understanding` |
| `goal` | 用户目标 |
| `inputs` | 输入资源和参数 |
| `expected_outputs` | 期望产物类型 |
| `success_criteria` | 成功标准 |
| `risk_level` | 风险等级 |
| `allowed_tools` | 允许使用的工具 |
| `budget` | token、耗时、调用次数或成本预算 |
| `human_review_policy` | 是否需要人工确认 |

### 5.1.5 Agent Adapter Protocol

Agent Runtime 不应要求所有 Agent 项目使用同一种编排框架，而应通过 adapter 接收不同项目。

最小协议：

| 方法 / 字段 | 说明 |
|-------------|------|
| `adapter_id` | 接入项目标识 |
| `trace_name` | trace 文件名 |
| `describe_contract()` | 返回 `TaskContract` |
| `run(context)` | 执行项目逻辑并返回 artifacts 与 evaluation |

Runtime 负责公共生命周期：

- 创建 trace。
- 记录 task started。
- 提供 tool call 记录入口。
- 记录 artifacts。
- 包装 evaluation artifact。
- 记录 task finished。

### 5.2 Artifact Protocol

定义 Agent 的结构化产物。

第一阶段建议支持：

| Artifact | 用途 |
|----------|------|
| `TextArtifact` | 摘要、回答、报告片段 |
| `ResearchArtifact` | 搜索结果、引用、证据摘要 |
| `RAGAnswerArtifact` | 答案、引用、检索证据 |
| `CodeRepairArtifact` | 修复说明、patch、验证结果 |
| `ErrorSummaryArtifact` | 错误分类、压缩 traceback、失败原因 |
| `EvaluationArtifact` | 评分、指标、失败项 |
| `ImageUnderstandingArtifact` | 可选扩展：图片/OCR/视觉结构化结果 |
| `TranscriptArtifact` | 可选扩展：语音转写结果 |

原则：

- 每个 artifact 必须有 schema。
- 每个 artifact 必须能被 trace 引用。
- 每个 artifact 必须能被 validator 校验。
- 重要 artifact 必须记录来源、模型、时间和成本。

### 5.3 Trace Recorder

定义可回放过程记录。

建议事件类型：

| 事件 | 说明 |
|------|------|
| `task_started` | 任务开始 |
| `step_started` / `step_finished` / `step_failed` / `step_skipped` | Runtime step 生命周期 |
| `model_called` | 模型调用 |
| `tool_called` | 工具调用 |
| `artifact_created` | 产物生成 |
| `validation_run` | 校验执行 |
| `evaluation_run` | 评估执行 |
| `guardrail_blocked` | 安全或权限拦截 |
| `human_review_requested` | 请求人工确认 |
| `task_finished` | 任务结束 |

第一阶段使用 JSONL 即可，不急于引入完整观测平台。

后续可以对照 Langfuse、Phoenix、LangSmith。

### 5.4 Tool Governance

工具不应只是函数调用，而应被 runtime 管理。

建议定义：

| 字段 | 说明 |
|------|------|
| `tool_name` | 工具名 |
| `risk_level` | 风险等级 |
| `allowed_paths` | 文件访问范围 |
| `network_policy` | 是否允许联网 |
| `approval_required` | 是否需要人工审批 |
| `timeout_seconds` | 执行超时 |
| `max_calls` | 最大调用次数 |
| `input_schema` | 参数 schema |
| `output_schema` | 返回 schema |

第一阶段优先接入 D-lite 的执行工具、安全检查和验证工具。

### 5.5 Runtime Observability 与 Evaluation

统一不同项目的运行结果观测与验证入口。这里的 evaluation 是 Runtime 的辅助能力，用来回答“是否完成、哪里失败、是否越界、能否复盘”，而不是把项目重新变成评测 runner。

| 评估对象 | 指标 |
|----------|------|
| RAG | 检索命中率、引用正确性、答案忠实度 |
| 内容生成 | 结构完整性、证据支撑、引用质量、评审通过率 |
| 自主调研 | 目标漂移、任务完成率、成本、trace 完整度 |
| 自愈 Agent | 修复成功率、安全拦截率、回归失败率、平均修复轮数 |
| 多模态实验 | OCR 准确性、时间戳准确性、人工复核通过率 |

第一阶段不追求复杂评分模型，先实现规则验证、结构化汇总和可回放证据。真实 runtime execution 应从任务输入开始执行链路；读取已有产物只能称为 observability adapter。

### 5.6 Human-in-the-loop

人工介入不应是临时 `input()`，而应是 runtime 状态的一部分。

建议终态：

| 状态 | 含义 |
|------|------|
| `passed` | 自动验证通过 |
| `failed` | 自动验证失败 |
| `blocked` | 被安全策略拦截 |
| `needs_human` | 需要人工确认 |
| `cancelled` | 人工取消 |

第一阶段可以只做本地确认记录，不需要 UI。

### 5.7 Small Model / Multimodal Track

这是可选扩展，不应阻塞 runtime 主线。

推荐最小实验：

| 实验 | 目标 |
|------|------|
| 图片/截图理解 | 小 VLM 生成 `ImageUnderstandingArtifact` |
| 音频转写 | ASR 生成 `TranscriptArtifact` |
| TTS 输出 | TTS 生成 `SpeechOutputArtifact`，进入审核和版本记录 |
| 编码小模型 worker | 只处理 scope 明确的小代码修复 |
| 大小模型协作 | 小模型抽取，大模型判断，runtime 记录证据链 |

## 6. 开发阶段

### E0：计划固化与目录搭建

当前状态：已完成。项目目录、README、Runtime Core 初始模块和原生报告治理场景已建立。

目标：建立项目骨架和最小文档。

任务：

- 创建 `practice-projects/05-agent-runtime-governance/`。
- 创建 README，说明目标、非目标、运行方式。
- 定义核心模块目录。
- 选择第一批对接样本：优先 D-lite。

验收：

- 目录结构清晰。
- README 能解释为什么项目 E 被重新定位。
- 能列出 E1-E4 的最小推进路径。

### E1：Task Contract 与 Artifact Protocol

当前状态：已完成第一版。已实现 `TaskContract`、基础 artifact、D-lite 映射产物，以及报告治理场景所需的文档质量、问题、改进计划、工具决策和人工审核产物。

目标：先把“任务”和“产物”稳定下来。

任务：

- 实现 `TaskContract`。
- 实现基础 artifact schema。
- 为 D-lite 创建 `self_heal` 类型任务契约。
- 将 D-lite 的结果映射为 `CodeRepairArtifact` 和 `ErrorSummaryArtifact`。

验收：

- 一个 D-lite challenge task 可以被包装成 TaskContract。
- 修复结果不再只是文本报告，而是结构化 artifact。
- schema 校验失败能被明确记录。

### E2：Trace Recorder

当前状态：已完成第一版。已支持 JSONL trace，记录 task、step、tool decision、tool call、artifact、evaluation、guardrail block、human review 和 task finished。已实现 `trace replay / summary` 工具，可输出人类可读时间线和机器可读 JSON 摘要。

目标：让过程可回放。

任务：

- 实现 JSONL trace recorder。
- 记录 task、model、tool、artifact、validation、final report。
- 给 D-lite 接入 trace 输出。
- 写一个 trace replay / summary 工具。

验收：

- 每次运行都生成 trace 文件。
- trace 能回答：做了什么、调用了什么、失败在哪里、为什么通过或失败。
- D-lite 的安全拦截和修复过程都能在 trace 中看到。

### E3：Tool Governance

当前状态：已完成第一版。已实现 `ToolRegistry`、`ToolPolicy`、`GovernedToolRunner`、`ToolDecisionArtifact`，支持 `allowed`、`blocked` 和 `needs_human` 决策。已增加目录级作用域策略：工具可以声明读路径和写路径入参，Runtime 在调用前检查路径是否位于 `allowed_read_dirs` / `allowed_write_dirs` 内。

目标：把工具调用纳入权限和风险控制。

任务：

- 定义 tool registry。
- 定义 tool policy。
- 给 D-lite 的执行器、安全检查器、验证器注册工具 metadata。
- 支持 `blocked` 和 `needs_human`。
- 支持文件读写目录作用域，阻止越权读取或写入。

验收：

- 高风险工具不能绕过 policy 调用。
- 危险代码可以进入 `blocked` 终态。
- 越权文件路径可以进入 `blocked` 终态。
- trace 中能看到被拦截原因。

### E4：Runtime Validation 与结果汇总

当前状态：已完成第一版。D-lite、A/B/C adapter 和 Runtime 原生报告治理场景都能输出统一 `EvaluationResult`。

目标：建立统一运行结果和验证结果入口。这里的 `EvaluationResult` 是终态表达和验证摘要，不代表 Runtime 的核心目标是评测。

任务：

- 定义 validation / evaluation case。
- 定义 evaluation result schema。
- 先接入 D-lite 的 8 个 challenge tasks。
- 汇总成功率、安全拦截率、平均修复轮数、失败原因。

验收：

- 一条命令可以跑完整 D-lite eval。
- 输出机器可读 JSON 和人类可读 summary。
- 能作为后续回归测试基线。

### E5：接入 A/B/C 的轻量观测评估

当前状态：已完成第一版。A/B/C 目前是轻量静态 observability adapter，只读取已有产物做 readiness / quality / artifact evaluation，不重新执行原始 Agent workflow，因此不能称为完整 Runtime 执行。
已补充 B 项目质量修复建议：内容创作团队 adapter 在输出 `ContentReportArtifact` 和 `EvaluationResult` 的同时，会根据确定性质量问题生成 `ImprovementPlanArtifact`，避免只给失败分数而没有后续行动入口。
已新增 `AgentAdapter` 协议，并将 A/B/C/D-lite adapter 迁移到统一 Runtime 生命周期。D-lite 仍保留内部自愈循环，但外层 task_started、artifact_created、evaluation_run 和 task_finished 已由 Runtime 统一记录。
已新增 B-runtime-lite：从 topic 开始执行最小内容生产交付链路，经过 `GovernedToolRunner` 调用生成大纲、写草稿、审阅草稿、生成改进计划、修订草稿、写最终报告和交付检查工具，作为 B 项目的第一个 runtime execution 样本。质量分数只作为 guardrail 和改进依据，不作为任务目标本身。
已新增 `RuntimeState / StepExecution`，B-runtime-lite 现在由 Runtime step 驱动，trace 中可以看到 `step_started` / `step_finished`，避免继续把项目做成评测 runner。
已新增 `RuntimeCheckpointStore`，通用 adapter 生命周期会在 step 开始、完成、失败、artifact 记录和任务结束时保存 `RuntimeState` checkpoint。
已新增最小 resume：`run_step(..., output_key=...)` 会缓存步骤输出；使用 `--resume` 时，已完成且有缓存输出的 step 会记录 `step_skipped` 并复用 checkpoint 输出。
已新增 `LocalArtifactStore`，B-runtime-lite 会把 outline、draft、draft review、improvement plan、final draft 和 delivery check 写入 `artifacts/`，state 中只保存 artifact ref。
已新增 `RuntimeRunLock`，通用 adapter 生命周期会在运行开始时创建本地 `.lock` 文件，阻止同一 adapter 并发写入同一组 trace、checkpoint 和 artifact；新格式 lock 记录 pid，并可清理 pid 已失效的 stale lock。
已新增可选 `run_id` 隔离；传入 `run_id` 后，trace、checkpoint、artifact、lock、manifest 和 B-runtime-lite 报告输出会进入对应子路径。当前仍是本地最小实现，尚未处理多 worker 并发策略。
已新增 `RuntimeRunManifest`，记录 run_id、adapter、trace、checkpoint、artifact root、状态、评分和摘要。

目标：验证 Runtime 的结构化观测、统一评估和 artifact 协议是否能跨项目复用，同时明确区分“观测已有产物”和“真实执行 Agent”。

任务：

- 给 A 接入 RAG 评估结果。
- 给 B 接入报告质量评估结果。
- 给 C 接入任务循环、成本和目标漂移评估结果。
- 不重写项目，只做 adapter。
- B 项目失败时输出结构化修复建议。
- A/B/C/D-lite adapter 使用统一 `AgentAdapter` 协议。
- A/B/C adapter 的文档和命令命名明确为 observability，不误称为 runtime execution。
- 为 B 项目补充一个最小 runtime execution adapter，避免 B 只停留在观测已有产物。
- B-runtime-lite 的成功标准以最终报告交付和修订完成为主，质量检查只作为 guardrail。

验收：

- A/B/C/D-lite 都能输出统一 `EvaluationArtifact`。
- B 项目能额外输出 `ImprovementPlanArtifact`。
- 能生成跨项目观测汇总报告。
- 能比较不同项目在 trace、成本、评估、安全上的成熟度。
- Runtime 能统一记录 adapter 的公共生命周期事件。
- B-runtime-lite trace 中能看到 `step_started`、`step_finished`、`tool_decision`、`tool_called`、artifact 和 final status 的完整执行链路。

### E6：Human-in-the-loop 与审批记录

当前状态：已完成最小闭环。报告治理场景中的高风险写入工具默认进入 `needs_human`，批准后才生成补丁建议文件；审核请求和审核决策都会进入 trace。

目标：将人工介入变成标准状态。

任务：

- 定义 `HumanReviewRequest`。
- 定义 `HumanReviewDecision`。
- 在高风险工具和低置信度评估中触发 `needs_human`。
- 先用本地 JSON 或命令行方式保存审批结果。

验收：

- 高风险动作不会自动继续。
- 人工确认记录进入 trace。
- final report 能说明哪些结果经过人工确认。

### E6.5：可选 LLM Reviewer

当前状态：已完成第一版。报告治理场景支持 `--llm-review`，通过 Runtime 工具治理调用外部 LLM，生成 `LLMReviewArtifact`。LLM 只提供辅助审阅意见，不决定最终 `passed` / `failed`。

目标：观察模型判断与确定性规则如何在 Runtime 中分层协作。

任务：

- 定义 `LLMReviewArtifact`。
- 将 LLM reviewer 注册为受治理工具。
- 要求 LLM reviewer 显式启用网络权限。
- 在 trace 中记录 reviewer 工具调用、工具决策和审阅 artifact。

验收：

- 不启用 `--llm-review` 时不会调用模型。
- 启用后生成结构化审阅 artifact。
- 最终状态仍由确定性 validator 和 Runtime 终态规则决定。

### E7：Small Model / Multimodal 扩展实验

目标：验证小模型和多模态能力如何作为 runtime skill 接入。

任务：

- 选择一个图片/OCR 小实验。
- 选择一个 ASR 转写小实验。
- 可选：选择一个编码小模型 worker 对照实验。
- 所有实验都必须输出 artifact、trace 和 eval。

验收：

- 小模型不是直接给最终答案，而是生成受校验 artifact。
- 大小模型协作过程可回放。
- 能记录模型、耗时、成本、失败样例。

## 7. 建议目录结构

```text
practice-projects/05-agent-runtime-governance/
  README.md
  runtime/
    contracts.py
    artifacts.py
    artifact_store.py
    state.py
    run_lock.py
    trace.py
    tools.py
    policies.py
    evaluation.py
    human_review.py
  adapters/
    d_lite_adapter.py
    rag_adapter.py
    content_team_adapter.py
    research_adapter.py
  eval_cases/
    d_lite_cases.json
  traces/
  reports/
  tests/
    test_contracts.py
    test_artifacts.py
    test_trace.py
    test_tool_policy.py
    test_evaluation.py
```

## 8. 推荐优先级

第一阶段只做这四件事：

```text
E1 Task Contract
E1 Artifact Protocol
E2 Trace Recorder
E4 D-lite Runtime Validation
```

原因：

- D-lite 已有最清晰的客观验证信号。
- 自愈场景天然需要安全、trace、验证和终态。
- 先接 D-lite 能最快证明 runtime 抽象是否有价值。
- 不需要引入新的复杂外部服务。

第二阶段再做：

```text
Tool Governance
Human-in-the-loop
A/B/C adapters
```

第三阶段再做：

```text
Small Model / Multimodal Track
Langfuse / Phoenix 对照
LangGraph 对照实现
```

## 9. 里程碑

| 里程碑 | 产出 | 判断标准 |
|--------|------|----------|
| M1：Runtime schema 成型 | TaskContract、Artifact、EvaluationResult | D-lite 可映射 |
| M2：Trace 可回放 | JSONL trace + summary | 能定位失败轮次和原因 |
| M3：D-lite 接入 | D-lite adapter + eval runner | 8 个 challenge tasks 可统一评估 |
| M4：工具治理 | Tool registry + policy | 危险动作可 blocked |
| M5：跨项目观测 | A/B/C/D-lite adapters | 能生成统一观测与验证报告，并区分 observability 和 runtime execution |
| M6：多模态小实验 | 图片/OCR 或 ASR artifact | 小模型能力可被 runtime 管理 |

## 10. 成功标准

项目 E 第一阶段完成时，应能回答：

1. 一个 Agent 任务的目标、输入、输出和成功标准在哪里定义？
2. Agent 产物是否有 schema，而不是自由文本？
3. 每一次模型调用、工具调用、校验和失败是否可追踪？
4. 危险工具是否能被拦截？
5. 修复成功是否由测试和验证证明？
6. 失败时是否能说明停在哪、为什么停、能否继续？
7. A/B/C/D-lite 是否能输出统一运行结果，并清楚区分 observability 和 runtime execution？

如果这些问题能被明确回答，本项目就达到了学习和方法论沉淀目标。

## 11. 风险与控制

| 风险 | 控制方式 |
|------|----------|
| 抽象过度 | 先接 D-lite，等需求出现再抽象 |
| 范围失控 | 明确不做通用框架、低代码平台和真实运维 |
| 只写文档不验证 | 每个阶段都必须有可运行测试或 eval |
| 评估形式化 | 优先用客观指标，LLM judge 只作为辅助 |
| 多模态过早复杂化 | 放到 E7，先做离线 artifact，不做实时系统 |
| 工具权限不清 | 所有工具先注册 policy，再允许调用 |

## 12. 与现有文档的关系

| 文档 | 关系 |
|------|------|
| `docs/practice-projects-plan.md` | 原始 A-E 项目矩阵，本计划是项目 E 的重新定位和后续推进主线 |
| `docs/concepts/agent-runtime-philosophy.md` | 提供 Runtime 八层模型和方法论背景 |
| `docs/concepts/agent-frameworks-and-services-landscape.md` | 提供框架、平台、观测、guardrails 和云服务选型参考 |
| `docs/concepts/multimodal-agent-capabilities-landscape.md` | 提供多模态和小模型扩展方向 |
| `docs/agent-runtime-governance-stage-summary.md` | 项目 E MVP 阶段总结，记录已实现能力、设计取舍和后续建议 |
| `practice-projects/04-self-healing-ops/` | 第一优先级接入对象 |

## 13. 下一步任务

当前 E0-E6.5 已完成第一版，项目 E 已达到 Agent Runtime & Governance Lab 的 MVP 状态。E-Mini Hardening 收尾也已完成：stale pid lock 清理、run manifest 和 LLM reviewer 最小指标已经落地。下一步不建议立即扩大到多模态，而是先做阶段性固化和工程收敛。

建议顺序：

1. 维护 `docs/agent-runtime-governance-stage-summary.md` 和 MVP 收束记录，作为阶段边界。
2. 继续压缩 tool input 摘要，避免 trace 中出现大段 markdown。
3. 逐步让 adapter 的工具调用也经过 `GovernedToolRunner`，补齐 tool decision trace。
4. 如继续工程化，优先选择策略文件、step retry 或第二真实场景中的一个小任务。
5. 再决定是否进入 E7 多模态小模型实验。

当前阶段的判断标准是：先保证 Runtime Core 的边界、文档、测试和运行命令稳定，再继续扩大能力范围。
