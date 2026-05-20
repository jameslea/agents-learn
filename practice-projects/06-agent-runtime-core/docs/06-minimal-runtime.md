# 阶段 6：最小 Runtime 串联

## 目录

- [能力定位](#能力定位)
- [当前状态](#当前状态)
- [实现文件](#实现文件)
- [核心对象](#核心对象)
- [最小场景](#最小场景)
- [串联关系](#串联关系)
- [运行方式](#运行方式)
- [Resume 语义](#resume-语义)
- [Blocked 语义](#blocked-语义)
- [验证方式](#验证方式)
- [核心概念](#核心概念)
- [经验教训](#经验教训)
- [当前边界](#当前边界)

## 能力定位

最小 Runtime 串联要把前五个阶段的能力组合成一个可运行的小型 Agent 场景。

目标不是做完整框架，而是验证这些公共能力能否支撑真实流程：

```text
contract -> state -> context -> memory -> step -> artifact -> trace -> checkpoint -> resume / blocked
```

## 当前状态

状态：`completed`

阶段 6 已经完成 `research_mini` 端到端最小验证。它不调用真实 LLM，而用确定性 step 模拟研究型 Agent，重点观察 Runtime Core 的公共支撑能力。

## 实现文件

相对代码根目录：`practice-projects/06-agent-runtime-core/`

```text
runtime_core/execution/minimal_runtime.py
runtime_core/execution/tool_policy.py
scenarios/research_mini/scenario.py
scripts/run_research_mini.py
tests/test_minimal_runtime.py
```

## 核心对象

| 对象 | 职责 |
|------|------|
| `MinimalRuntime` | 薄封装 state、context、memory、artifact、checkpoint 和 trace |
| `BlockedReason` | blocked 终态的人类可读原因和处理建议 |
| `ToolPolicy` | 工具风险、只读属性和审批要求 |
| `ToolPolicyChecker` | 工具调用前的最小策略检查 |
| `ResearchMiniRunResult` | 端到端 demo 的运行摘要 |

`MinimalRuntime` 不包含业务 step。业务逻辑放在 `scenarios/research_mini/scenario.py`，避免 runtime 核心和场景代码混在一起。

## 最小场景

`research_mini` 流程：

```text
plan_research
collect_evidence -> EvidenceTable
write_report -> DraftReport
review_report -> ReviewResult
```

这个场景能覆盖：

- `TaskContract`：定义任务目标和期望产物。
- `RuntimeState`：记录 step 进度。
- `ContextBuilder`：为每个 step 构造工作视图。
- `MemoryStore`：提供项目写作偏好。
- `ArtifactStore`：在 step 之间交接 schema artifact。
- `TraceRecorder`：记录 task、step、artifact 和工具策略事件。
- `FileCheckpointStore`：支持中断后恢复。
- `ToolPolicyChecker`：演示工具策略导致 blocked。

## 串联关系

```text
run_research_mini.py
  -> scenarios.research_mini.run_research_mini()
    -> MinimalRuntime
      -> TaskContract
      -> RuntimeState
      -> ContextBuilder
      -> MemoryStore
      -> ArtifactStore
      -> TraceRecorder / TraceReader
      -> FileCheckpointStore
```

Artifact store 当前仍是内存版。为了支持命令级 resume，`MinimalRuntime` 额外保存一个最小 `artifacts.json` 快照。它不是完整持久化 artifact store，只是阶段 6 为验证恢复语义增加的轻量桥接。

## 运行方式

完整运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset
```

中断后恢复：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --stop-after collect_evidence
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py
```

blocked 演示：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --force-blocked
```

建议并行运行 demo 时显式传入不同 `--workdir`，避免多个进程写同一个 checkpoint / trace 文件。

## Resume 语义

1. 每个 step 通过后保存 checkpoint。
2. 生成 artifact 后保存 `artifacts.json` 快照。
3. 使用 `--stop-after collect_evidence` 可模拟中断。
4. 再次运行时读取 checkpoint 和 artifact snapshot。
5. 已通过 step 会被记录为 skipped。
6. 下游 step 可以继续读取上游 artifact，避免从头重跑。

## Blocked 语义

`--force-blocked` 会在 `write_report` 阶段模拟一个违反工具策略的调用：

```text
read-only tool cannot run mutating request: markdown_writer
```

Runtime 会：

- 将任务状态设为 `blocked`。
- 将当前 step 标记为 `BLOCKED`。
- 写入 `human_required` trace 事件。
- 输出 `BlockedReason`，包含原因和人工处理建议。

## 验证方式

运行测试：

```bash
python3 -m pytest practice-projects/06-agent-runtime-core/tests/test_minimal_runtime.py
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

当前测试覆盖：

- 完整流程可以完成。
- 中断后可以基于 checkpoint 和 artifact snapshot 恢复。
- 工具策略可以触发 blocked。
- trace 不保存完整 artifact payload。
- 工具策略能拦截未注册工具和只读工具的写入请求。

## 核心概念

- Runtime Core 应提供公共支撑能力，不应吞掉场景业务逻辑。
- 具体 Agent 场景应通过 contract、artifact、trace 等结构化接口和 Runtime 交互。
- 命令级 resume 不只需要 state，还需要恢复下游 step 所需的 artifact 引用或快照。
- blocked 是一种有意义的终态，不是异常崩溃；它应该包含人能处理的原因和建议。
- 最小工具策略可以先覆盖风险等级、只读约束和审批要求，再逐步扩展。

## 经验教训

- 前五个能力单独成立，不等于自然能串起来；真正串联时会暴露 artifact 持久化、运行目录隔离和状态恢复边界。
- Runtime 保持薄封装更容易理解。业务 step 放在 scenario 中，Runtime 只负责公共能力。
- JSONL trace 适合本地复盘，但真实运行后可以增加 Langfuse 等可选 backend。
- 并行 demo 共享同一个 workdir 会污染 trace 和 checkpoint；真实 Runtime 需要明确 run id 或隔离目录。
- 预算和延迟治理当前只通过 step 时间和 trace 观察，尚未形成完整预算系统。

## 当前边界

本阶段仍不做：

- 真实 LLM 调用。
- Langfuse trace backend。
- Web UI。
- 插件市场。
- 多租户权限系统。
- 复杂多 Agent。
- 企业级部署。
- 完整预算、成本和并发治理。

这一步证明 Runtime Core 小核心可以支撑一个真实但有限的 Agent 流程，但它仍然只是探索性最小实现。
