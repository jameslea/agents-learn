# Agent Runtime & Governance Lab 阶段总结

> 更新时间：2026-05-18
>
> 本文总结项目 E 重新定位后的第一阶段成果。当前阶段重点不是继续堆 Agent demo，而是验证 Agent Runtime 中那些支撑可控、可评估、可复盘的基础能力。

## 1. 当前结论

项目 E 已经从原计划中的“评估与安全防线附属模块”，调整为一个独立的 **Agent Runtime & Governance Lab**。

当前已经达到最小可运行版本：

```text
TaskContract
  -> RuntimeState / StepExecution
  -> ToolPolicy / GovernedToolRunner
  -> Artifact
  -> EvaluationResult
  -> Runtime Trace
  -> Trace Replay
  -> Human Review / LLM Review
```

这说明项目方向与新的目标是一致的：我们不是在构建一个万能 Agent，而是在沉淀一套能为不同 Agent 项目提供公共环境和治理能力的运行时框架。

更准确的定位是：

```text
Agent Project = 具体业务逻辑 / 策略 / 技能组合
Agent Runtime = 执行环境 / 治理规则 / 观测评估 / 公共设施
```

## 2. 已实现能力

### 2.1 Runtime Core

| 能力 | 当前实现 |
|------|----------|
| 任务契约 | `TaskContract` 定义任务类型、目标、输入、成功标准、风险等级、允许工具和预算 |
| 运行状态 | `RuntimeState` 和 `StepExecution` 记录任务步骤、状态值、产物引用和 step lifecycle |
| 状态持久化 | `RuntimeCheckpointStore` 在 step 开始、结束、失败、artifact 记录和任务结束时保存 state checkpoint |
| 最小恢复 | `run_step(..., output_key=...)` 支持 resume 时跳过已完成且有缓存输出的 step |
| 产物存储 | `LocalArtifactStore` 将较大的 step 输出保存到 `artifacts/`，state 和 trace 只保存 artifact ref |
| 运行锁 | `RuntimeRunLock` 通过最小本地文件锁阻止同一 adapter 并发写入，并可清理记录了失效 pid 的 stale lock |
| 运行隔离 | `run_id` 可将 trace、checkpoint、artifact、lock、manifest 和 B-runtime-lite 报告输出隔离到一次运行的子路径 |
| 运行索引 | `RuntimeRunManifest` 记录 run_id、adapter、trace、checkpoint、artifact root、状态和摘要 |
| 项目适配 | `AgentAdapter` 定义不同 Agent 项目接入 Runtime 的最小协议 |
| 结构化产物 | `Artifact` 协议覆盖代码修复、评估、报告质量、问题、改进计划、LLM review、人工审核等 |
| 统一评估 | `EvaluationResult` 和 `EvaluationSummary` 统一表达 passed / failed / blocked / needs_human |
| Trace 记录 | `RuntimeTraceRecorder` 将任务、工具、artifact、评估、阻塞和人工审核写入 JSONL |
| Trace 回放 | `trace_replay.py` 将 JSONL 还原为时间线和机器可读摘要 |
| 工具治理 | `ToolRegistry`、`ToolPolicy`、`GovernedToolRunner` 管理工具权限、风险、次数和决策 |
| 安全边界 | 支持路径读写作用域、网络权限、高风险审批和 guardrail block |
| 人工介入 | 高风险工具默认进入 `needs_human`，批准后才执行 |

### 2.2 Runtime 原生场景

当前主线场景是报告质量治理：

```text
Markdown report
  -> deterministic quality metrics
  -> structured issues
  -> improvement plan
  -> optional LLM reviewer
  -> optional high-risk patch proposal
  -> evaluation result
  -> replayable trace
```

这个场景不依赖 A/B/C/D-lite，能够直接观察 Runtime Core 的价值。

已支持：

- 文档质量度量：字符数、标题、列表、表格、引用、薄弱章节、证据边界等。
- 问题结构化：将质量问题转成 `IssueArtifact`。
- 改进计划：生成 `ImprovementPlanArtifact`。
- 可选 LLM reviewer：生成 `LLMReviewArtifact`，但不决定最终通过或失败。
- 高风险补丁建议：未批准时进入 `needs_human`，批准后才写出建议文件。

### 2.3 旧项目 Adapter

A/B/C/D-lite 已作为兼容样本和回归样本接入 Runtime，但当前语义需要区分：

- A/B/C 是 observability adapter：读取已有项目产物，做 readiness / quality / artifact evaluation，不重新执行原始 Agent workflow。
- D-lite 是 runtime execution adapter：通过 Runtime 外层生命周期实际运行已有 self-heal loop。
- B-runtime-lite 是新增 runtime execution adapter：从 topic 开始执行一个最小内容生产链路，用来观察 B 项目 Runtime 化会遇到的问题。

| 项目 | 接入方式 | 当前定位 |
|------|----------|----------|
| A：知识库问答 | 静态 readiness / 证据检查 | RAG 兼容样本 |
| B：内容创作团队 | 报告质量评估 + 改进计划 artifact | 内容质量治理样本 |
| B-runtime-lite：内容生产最小执行 | RuntimeState 驱动大纲、草稿、审阅、改进计划、修订、写最终文件、交付检查 | 内容生产 Runtime 样本 |
| C：自主调研助手 | 最终报告结构评估 | 长任务输出样本 |
| D-lite：自愈最小实验 | 自愈任务结果映射为 Runtime artifact 和 eval | 安全与自愈回归样本 |

这里的目标不是重写旧项目，而是验证 Runtime 抽象能否包住不同类型的 Agent 实践结果。

当前 A/B/C/D-lite 已通过 `AgentAdapter` 协议接入，统一由 Runtime 负责 task_started、artifact_created、evaluation_run 和 task_finished 这些公共生命周期事件。需要注意：A/B/C 的 trace 表示“观测评估过程”，不是原始 Agent 执行过程；D-lite 和 B-runtime-lite 的 trace 才表示真实执行。D-lite 仍保留内部自愈循环，但外层任务契约、trace、artifact 和 evaluation 已纳入统一 Runtime 生命周期。

## 3. 与计划目标的对齐

当前实现与方法论文档中提出的关键项基本对齐：

| 方法论项 | 当前状态 |
|----------|----------|
| 状态持久化 | 通过 `RuntimeCheckpointStore` 保存 step lifecycle、artifact ref、状态值和终态 |
| 上下文治理 | 通过结构化 artifact 减少长对话交接 |
| 工具权限 | 通过 `ToolPolicy` 控制 allowed tools |
| 安全边界 | 通过路径作用域、网络权限、高风险审批实现 |
| 结构化产物 | 已覆盖核心场景与旧项目 adapter |
| 可回放 trace | 已支持 JSONL 记录和 replay |
| 评估体系 | 已有统一 `EvaluationResult` 和确定性评分，但定位为 Runtime 配套验证能力 |
| 人工介入 | 已支持 `needs_human` 和审核记录 |
| 成本和延迟控制 | LLM reviewer 默认关闭；启用时记录 provider、model、latency、status 和 failure reason；调用失败不覆盖确定性评估结果 |
| 部署与版本治理 | 暂未展开，当前仍是本地实验项目 |

## 3.5 AgentAdapter 协议

当前新增的核心方向是把 Runtime 明确为“适配不同 Agent 项目的公共运行环境”。

最小 adapter 协议包括：

| 方法 / 字段 | 作用 |
|-------------|------|
| `adapter_id` | 标识接入项目或场景 |
| `trace_name` | 指定该 adapter 的 trace 文件名 |
| `describe_contract()` | 返回 Runtime 可理解的 `TaskContract` |
| `run(context)` | 执行项目逻辑，返回 `AgentRunResult` |

Runtime 统一提供：

- 创建 trace recorder。
- 记录 task started。
- 提供 `AdapterRunContext.record_tool_call(...)`。
- 记录 adapter 返回的 artifacts。
- 包装 evaluation artifact。
- 记录 task finished。

这个协议让不同 Agent 项目可以保留内部范式，同时共享 Runtime 的公共治理与观测能力。

## 4. 设计取舍

### 4.1 保留确定性评估作为最终裁决

LLM reviewer 只生成辅助意见，不直接改变最终 `passed` / `failed`。

这样做的原因是：当前阶段的目标是验证 Runtime 的可控性，而不是把裁决权交给不稳定模型输出。

### 4.2 旧项目只做 adapter，不重写

A/B/C/D-lite 的价值在于提供真实样本和回归基线。如果强行重写，会把 Runtime 验证变成旧项目迁移工程，偏离当前阶段目标。

### 4.3 工具治理先做本地边界

当前优先实现了本地路径、网络、高风险审批和调用次数控制。云环境、凭证系统、RBAC、审计平台暂不进入范围。

### 4.4 Trace 先使用 JSONL

JSONL 足够支撑学习、测试和回放。Langfuse、Phoenix、LangSmith 等外部平台可以后续对照接入，但不是 MVP 必需项。

### 4.5 B-runtime-lite 暴露的问题

把 B 项目从 observability 推进到最小 runtime execution 后，暴露出几个实际问题：

| 问题 | 观察 |
|------|------|
| 不能把观测评估直接称为 Runtime | A/B/C 读取已有产物只能算 observability；必须从输入开始执行链路，才是 runtime execution |
| 原 B 多角色系统太重 | 直接迁移原 B 会把任务拖回多角色调试，因此先抽取 topic -> draft -> review -> plan -> revise -> final report 的最小交付闭环 |
| 写文件必须进入工具治理 | 生成报告写入 `reports/` 是副作用，必须通过 `ToolPolicy` 的写目录作用域控制 |
| 质量检查不能成为任务本身 | B-runtime-lite 的最终状态改为由交付产物决定，质量分数只作为 guardrail 和改进依据 |
| 缺少 RuntimeState 会继续滑向评测 | 已补充 `RuntimeState / StepExecution`，让 B-runtime-lite 按 step 执行，而不是一次函数返回结果 |
| 没有 checkpoint 就无法恢复 | 已补充 `RuntimeCheckpointStore` 和最小 resume；当前支持复用已完成 step 输出，但还没有通用 step graph 调度 |
| 并发写入会污染 trace | 已补充最小本地运行锁、stale pid lock 清理和可选 `run_id` 隔离；后续如需并发 worker 再扩展策略 |
| trace 容易记录过多输入 | 已补充 `LocalArtifactStore`，B-runtime-lite 的大段产物改为 artifact ref；后续还要继续压缩 tool input 摘要 |
| 确定性 writer 质量有限 | 当前样本能跑通 Runtime 链路，但不代表原 B 项目的内容智能已经迁移；后续可接入 LLM writer 并记录 provider / latency / cost |

## 5. 当前代码结构复查

当前结构总体清晰：

```text
runtime/       # Runtime Core：契约、产物、工具治理、trace、评估
scenarios/     # Runtime 原生场景
adapters/      # 旧项目兼容接入
tests/         # Runtime Core、场景和 adapter 回归测试
run_*.py       # CLI 入口
```

暂不建议进行大重构，但有几个后续可优化点：

| 问题 | 建议 |
|------|------|
| `scenario.py` 已承载较多流程逻辑 | 后续可拆为 metrics、issues、patch、evaluation 子模块 |
| `ToolPolicy` 仍是内存策略 | 后续可引入策略文件或 YAML/JSON schema |
| adapter 内部工具调用还没有全部走 `GovernedToolRunner` | 可逐步把 A/B/C/D-lite adapter 的工具调用纳入 tool decision trace |
| trace 还没有完整 model cost 字段 | 当前已有 LLM reviewer latency/status；后续可补 token 和 cost |
| 运行锁仍是本地最小实现 | 当前只处理本地文件锁；后续如需多 worker 再设计并发策略 |

这些不是当前 MVP 的阻塞问题。

## 6. 运行命令

运行 Runtime 原生报告治理：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py
```

启用 LLM reviewer：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py --llm-review
```

触发高风险补丁建议并批准：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py --request-patch --approve-high-risk
```

观测 A/B/C 已有项目产物：

```bash
python3 practice-projects/05-agent-runtime-governance/run_project_observability.py
```

观测 A/B/C，并同时实际执行 D-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_project_observability.py --run-d-lite
```

运行 B-runtime-lite 内容生产执行链路：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py
```

运行 D-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_d_lite_runtime.py
```

回放 trace：

```bash
python3 practice-projects/05-agent-runtime-governance/run_trace_replay.py
```

运行测试：

```bash
python3 -m pytest practice-projects/05-agent-runtime-governance/tests
```

## 7. 当前完成度

如果以“Agent Runtime & Governance Lab 的最小可运行版本”为标准，当前阶段可以认为 **MVP 已完成**。

已完成的关键闭环：

- 有任务入口契约。
- 有受治理的工具调用。
- 有结构化产物。
- 有确定性评估。
- 有 trace 和 replay。
- 有 `AgentAdapter` 适配协议。
- 有安全阻塞。
- 有人工介入。
- 有可选 LLM reviewer。
- 有旧项目 adapter 回归样本。
- 有 `RuntimeState / StepExecution`、checkpoint 和最小 resume。
- 有 `ArtifactStore` 管理大段中间产物。
- 有 `RuntimeRunLock`、stale pid lock 清理和可选 `run_id` 运行隔离。
- 有 `RuntimeRunManifest` 运行索引。
- 有 LLM reviewer provider / model / latency / status 最小指标。

本阶段的收束记录见：

- `docs/agent-runtime-governance-mvp-closure.md`

## 8. 后续建议

E-Mini Hardening 收尾已完成。先暂缓多模态扩展，当前更值得做的是在两个方向中选择一个继续推进：

1. Runtime 工程化增强：策略文件、step retry、更多 LLM metrics。
2. 第二个真实 Agent 场景：验证 Runtime 是否能适配内容生产以外的执行链路。

这样可以避免在 Runtime Core 尚未完全固化时继续扩大范围。
