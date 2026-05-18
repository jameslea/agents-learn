# Agent Runtime & Governance Lab

> 最小可运行目标：实现独立 Runtime Core，并用一个真实可运行的报告治理 Agent 场景观察 task contract、tool policy、artifact、trace、evaluation 和 human-in-the-loop。

## 定位

本项目是项目 E 的重新落地版本。它不再只是 A-D 的横向评估脚本，而是一个最小 Agent Runtime & Governance 实践项目。

更准确地说，本项目把 Agent Runtime 视为不同 Agent 项目的公共运行环境：

```text
Agent Project
  -> AgentAdapter
  -> TaskContract
  -> RuntimeState / StepExecution
  -> Artifact Store
  -> Runtime lifecycle
  -> Artifact / EvaluationResult / Trace
```

具体 Agent 可以采用不同范式，Runtime 只提供公共支持：任务入口、步骤状态、结构化产物、工具治理、可回放 trace、统一终态和人工介入。评估和观测只是配套能力，不是 Runtime 的目标本身。

当前原生示例是报告治理场景：

```text
Markdown report
  -> TaskContract
  -> ToolPolicy / ToolDecisionArtifact
  -> DocumentQualityArtifact / IssueArtifact / ImprovementPlanArtifact
  -> optional HumanReviewRequestArtifact
  -> EvaluationResult
  -> Runtime trace JSONL
```

它用于观察一个 Agent Runtime 最小闭环：任务契约、工具权限、安全边界、结构化产物、可回放 trace、评估体系和人工介入。

A/B/C/D-lite adapter 用来验证 Runtime 对不同 Agent 项目的适配能力，但它们当前不是同一种执行语义：

第一条是 D-lite 自愈链路：

```text
D-lite challenge task
  -> DLiteTaskAdapter
  -> TaskContract
  -> Runtime lifecycle
  -> existing D-lite self-heal loop
  -> CodeRepairArtifact / ErrorSummaryArtifact
  -> EvaluationResult
  -> Runtime trace JSONL
  -> FinalReport
```

第二条是项目观测链路。A/B/C 当前只读取已有产物做 readiness / quality / artifact evaluation，不重新运行原始 Agent workflow，因此更准确地说是 observability adapter，而不是完整 runtime execution：

```text
A/B/C existing project output
  -> TaskContract
  -> observability adapter
  -> structured Artifact
  -> EvaluationResult
  -> observability trace JSONL
  -> cross-project summary
```

## 非目标

- 不重写 D-lite 自愈逻辑。
- 不做通用 Agent 框架。
- 不接入真实运维环境。
- 不引入外部观测平台。
- 不实现 UI。

## 运行

运行全部 D-lite challenge tasks：

```bash
python3 practice-projects/05-agent-runtime-governance/run_d_lite_runtime.py
```

只运行指定任务：

```bash
python3 practice-projects/05-agent-runtime-governance/run_d_lite_runtime.py task1_broken_import.py
```

输出：

- `traces/*.jsonl`：统一 runtime trace。
- `reports/d_lite_summary.json`：机器可读评估摘要。
- 终端 summary：人类可读结果。

观测 A/B/C 已有项目产物：

```bash
python3 practice-projects/05-agent-runtime-governance/run_project_observability.py
```

默认会运行：

- A：RAG 项目静态 readiness / 证据检查。
- B：内容创作团队最终报告质量评估，并生成 `ImprovementPlanArtifact` 修复建议。
- C：自主调研助手最终报告结构评估。

如果要同时实际执行 D-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_project_observability.py --run-d-lite
```

旧入口 `run_project_runtime.py --include-d-lite` 暂时保留为兼容命令，但不再作为推荐用法。原因是 A/B/C 默认路径只是观测已有产物，严格说不能称为 runtime execution。

实际执行 B-runtime-lite 内容生产链路：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py
```

这条链路会从 topic 开始交付最终报告，经过 `GovernedToolRunner` 执行大纲、草稿、草稿审阅、改进计划、修订、写最终文件和交付检查，并生成 `content_runtime_lite.runtime.jsonl`。质量分数只作为 guardrail 指标，不作为任务目标本身。它是 B 项目的最小 runtime execution 样本，不等同于原 B 项目的完整多角色系统。

该链路已经使用 `RuntimeState / StepExecution` 管理步骤状态。trace 中可以看到 `step_started` / `step_finished` 事件，工具调用嵌在具体 step 内部。每个 step 开始和结束后，Runtime 也会保存 `state/*.json` checkpoint，供失败复盘和后续 resume 设计使用。

大段中间产物不会直接塞进 state。B-runtime-lite 会把 outline、draft、draft review、improvement plan、final draft 和 delivery check 写入 `artifacts/content_runtime_lite/`，`RuntimeState.values` 只保存 artifact ref。

从 checkpoint 恢复 B-runtime-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py --resume
```

隔离一次具名运行：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py --run-id experiment-001
```

自动生成一个时间戳 run id：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py --run-id
```

当前 resume 是最小版本：如果某个 step 已完成且 `RuntimeState.values` 中有缓存输出，Runtime 会记录 `step_skipped` 并复用该输出；没有缓存或失败的 step 会重新执行。Runtime 已增加最小本地运行锁，避免同一个 adapter 同时写入同一组 trace/checkpoint/artifact；如果传入 `run_id`，trace、checkpoint、artifact、lock、manifest 以及 B-runtime-lite 的报告输出会进入对应子目录。若进程被强制终止，Runtime 会自动清理记录了失效 pid 的 stale lock；无法判断 pid 的旧格式 lock 仍需要人工检查。

运行 Runtime 原生场景：文档/报告质量治理 Agent。

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py
```

这个场景不依赖 A/B/C/D-lite。它会读取一个 Markdown 文档，经过受 ToolPolicy 管理的工具调用，生成：

- `DocumentQualityArtifact`
- `IssueArtifact`
- `ImprovementPlanArtifact`
- 可选 `LLMReviewArtifact`
- `ToolDecisionArtifact`
- 可选 `HumanReviewRequestArtifact` / `HumanReviewDecisionArtifact`
- `EvaluationResult`
- JSONL runtime trace

启用可选 LLM reviewer：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py --llm-review
```

LLM reviewer 只生成辅助审阅意见，不决定最终 `passed` / `failed`。最终状态仍由确定性质量规则、工具治理和人工审核状态决定。
Runtime 会记录 LLM reviewer 的 provider、model、latency、status 和 failure reason 字段，作为最小成本/延迟观测基础。LLM reviewer 调用失败时会记录失败指标，但不会覆盖确定性评估结果。

触发高风险写入工具，但不批准：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py --request-patch
```

此时 Runtime 会返回 `needs_human`，记录人工审核请求，不写补丁文件。

批准高风险写入工具：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py --request-patch --approve-high-risk
```

此时 Runtime 会记录人工审核决策，并在 `reports/` 下生成建议补丁文件。

工具治理会同时检查权限、风险、人工审批和路径作用域。当前报告治理场景中：

- `report.read_and_measure` 只能读取目标文档所在目录下的路径。
- `report.llm_review` 需要显式启用网络权限。
- `report.write_improvement_patch` 只能写入 Runtime 允许的输出目录。
- 越权路径会进入 `blocked`，并在 trace 中记录 `guardrail_blocked`。

回放最近一次 trace：

```bash
python3 practice-projects/05-agent-runtime-governance/run_trace_replay.py
```

回放指定 trace：

```bash
python3 practice-projects/05-agent-runtime-governance/run_trace_replay.py practice-projects/05-agent-runtime-governance/traces/agent_runtime_note.report_governance.runtime.jsonl
```

输出机器可读摘要：

```bash
python3 practice-projects/05-agent-runtime-governance/run_trace_replay.py --json
```

## 当前模块

| 模块 | 作用 |
|------|------|
| `runtime/contracts.py` | 定义任务契约、预算、人工确认策略 |
| `runtime/state.py` | 定义 RuntimeState、StepExecution、步骤状态和 checkpoint store |
| `runtime/artifact_store.py` | 定义本地 Artifact Store 和 ArtifactRef |
| `runtime/agent_adapter.py` | 定义 Agent 项目接入 Runtime 的最小协议、统一生命周期和可选 run_id 隔离 |
| `runtime/artifacts.py` | 定义结构化产物，包括工具决策和人工审核产物 |
| `runtime/manifest.py` | 定义一次运行的 manifest，记录 trace、checkpoint、artifact root 和终态 |
| `runtime/run_lock.py` | 定义最小本地运行锁，避免同一 adapter 并发写入同一组运行产物 |
| `runtime/trace.py` | 定义 JSONL trace recorder |
| `runtime/evaluation.py` | 定义评估结果和汇总 |
| `runtime/tools.py` | 定义工具注册、工具策略、受控调用和治理决策 |
| `runtime/trace_replay.py` | 读取 JSONL trace，生成摘要和可读时间线 |
| `adapters/d_lite_adapter.py` | 将 D-lite 自愈任务接入 runtime |
| `adapters/rag_adapter.py` | 将 A 项目 RAG readiness 接入 runtime |
| `adapters/content_team_adapter.py` | 将 B 项目报告质量评估接入 runtime |
| `adapters/content_runtime_adapter.py` | B-runtime-lite，实际执行最小内容生产链路 |
| `adapters/research_adapter.py` | 将 C 项目调研报告评估接入 runtime |
| `run_d_lite_runtime.py` | 最小 CLI |
| `run_content_runtime.py` | 运行 B-runtime-lite 内容生产 runtime execution |
| `run_project_observability.py` | 跨项目观测汇总 CLI，默认观测 A/B/C 已有产物，可选执行 D-lite |
| `run_project_runtime.py` | 兼容旧命令的 wrapper，不再作为推荐入口 |
| `scenarios/report_governance/` | Runtime 原生文档质量治理场景 |
| `run_report_governance.py` | 运行原生场景的 CLI |
| `run_trace_replay.py` | 回放 runtime trace 的 CLI |

## 阶段总结

当前 MVP 阶段总结见：

- `docs/agent-runtime-governance-stage-summary.md`
- `docs/agent-runtime-governance-mvp-closure.md`

阶段总结记录当前 Runtime Core 已实现能力、与计划目标的对齐、设计取舍、结构复查和后续建议。MVP 收束记录用于冻结当前阶段边界、验收命令、已知风险和后续分支。

## 下一步

当前 MVP 已可阶段性收束，E-Mini Hardening 收尾也已完成。后续先暂缓多模态扩展，优先在两个方向中选择一个继续推进：

1. Runtime 工程化增强：策略文件、step retry、更多 LLM metrics。
2. 第二个真实 Agent 场景：验证 Runtime 是否能适配内容生产以外的执行链路。
