# Agent Runtime Core 小步验证项目

## 项目定位

本项目用于验证 Agent Runtime 的核心公共能力。当前阶段不追求完整生产级 Runtime，而是围绕上下文、状态、记忆、产物、trace 和可恢复执行做小步验证。

对应计划文档：[docs/agent-core-capabilities-validation-plan.md](../../docs/agent-core-capabilities-validation-plan.md)。

Runtime Core 的包职责、公开 API 和依赖边界说明见：[runtime-core-architecture.md](docs/runtime-core-architecture.md)。

Agent 系统非功能能力的横向总览见：[agent-non-functional-capabilities-overview.md](docs/agent-non-functional-capabilities-overview.md)。

## 当前进度

阶段 1：Context Builder 已完成最小验证。
阶段 2：Memory / State 分层已完成最小验证。
阶段 3：Checkpoint / Resume 已完成最小验证。
阶段 4：Schema Artifact 交接已完成最小验证。
阶段 5：Trace 与复盘已完成最小验证。
阶段 6：最小 Runtime 串联已完成最小验证。
阶段 7：code_review_mini 场景试验已完成最小验证。
阶段 8：Workflow / Agent 选择策略已完成文档化。

已具备：

- 最小任务入口契约：`TaskContract`。
- 最小任务状态模型：`RuntimeState`。
- 最小上下文构造器：`ContextBuilder`。
- 上下文策略：`ContextPolicy`。
- 统一候选模型：`ContextCandidate`。
- 上下文指标：`ContextMetrics`。
- 正式记忆记录：`MemoryRecord`。
- 轻量内存记忆库：`MemoryStore`，覆盖写入、验证、检索、失效和替换。
- 正式结构化产物记录：`ArtifactRecord`。
- Schema Artifact 定义：`EvidenceTable`、`DraftReport`、`ReviewResult`。
- 轻量内存 artifact store：`ArtifactStore`，覆盖保存、读取、schema 校验和消费检查。
- JSONL trace：`TraceRecorder`、`TraceReader`、`TraceReplaySummary`。
- 本地 checkpoint 存储：`FileCheckpointStore`。
- 顺序 step 执行器：`StepRunner`。
- 最小 Runtime 串联器：`MinimalRuntime`。
- 最小工具策略检查：`ToolPolicyChecker`。
- `research_mini` 端到端场景。
- `code_review_mini` 场景驱动 Runtime Core 复用试验。
- 可见性、信任等级、敏感候选拦截和 required context 检查。
- 可运行 demo 和测试。

尚未实现：

- 持久化 memory store。
- 持久化 artifact store。
- 持久化 trace store。
- 完整 tool policy、budget、latency 治理。
- Langfuse 等外部 trace backend。
- 向量检索和 LLM 自动摘要。

## 运行方式

运行 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_context_demo.py
```

默认输出为适合人工阅读的过程摘要。如果需要完整 `ContextBundle` JSON：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_context_demo.py --format json
```

运行 Memory / State / Artifact 分层 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_memory_state_demo.py
```

运行 Checkpoint / Resume demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_resume_demo.py
```

运行 Schema Artifact 交接 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_artifact_handoff_demo.py
```

运行 Trace 与复盘 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_trace_demo.py
```

运行最小 Runtime 串联 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset
```

运行代码审查场景 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset
```

使用真实 LLM 代码审查：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --llm
```

指定 LLM provider / model 并观察耗时：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --llm --provider minimax --model MiniMax-M2.7
```

演示中断后恢复：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --stop-after collect_evidence
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py
```

演示 blocked：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_research_mini.py --reset --force-blocked
```

运行测试：

```bash
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

## 目录结构

```text
practice-projects/06-agent-runtime-core/
  README.md
  docs/
    01-context-builder.md
    02-memory-state.md
    03-checkpoint-resume.md
    04-schema-artifact.md
    05-trace-replay.md
    06-minimal-runtime.md
    07-code-review-mini.md
    08-workflow-agent-selection.md
    agent-non-functional-capabilities-overview.md
    runtime-core-architecture.md
  runtime_core/
    __init__.py
    artifact/
      record.py
      store.py
      validation.py
    context/
      source.py
      candidate.py
      selection.py
      policy.py
      bundle.py
      builder.py
      rules/
        budget.py
        relevance.py
        required.py
    execution/
      minimal_runtime.py
      step_runner.py
      tool_policy.py
    memory/
      record.py
      proposal.py
      gate.py
      query.py
      store.py
      rules/
        scoring.py
    observability/
      checkpoint/
        file_store.py
        record.py
      trace/
        event.py
        recorder.py
        reader.py
        replay.py
        rules/
          redaction.py
    task/
      contract.py
      state.py
  scenarios/
    code_review_mini/
      __init__.py
      llm_reviewer.py
      sample_target.py
      schemas.py
      scenario.py
    research_mini/
      __init__.py
      schemas.py
      scenario.py
  scripts/
    run_context_demo.py
    run_code_review_mini.py
    run_artifact_handoff_demo.py
    run_memory_state_demo.py
    run_research_mini.py
    run_resume_demo.py
    run_trace_demo.py
  tests/
    conftest.py
    test_checkpoint_resume.py
    test_context_builder.py
    test_memory_state_boundaries.py
    test_minimal_runtime.py
    test_schema_artifact.py
    test_trace_replay.py
```

## 文档与代码组织关系

`docs/` 按验证阶段和场景设计方法组织，回答“这个能力为什么重要、如何验证、有哪些经验教训，以及新场景应如何选择 workflow / agent 模式”。
`runtime_core/` 按 Runtime 领域职责组织，回答“这些能力在代码中由哪些公共模块承载”。

二者不是一一对应关系。同一个阶段通常会涉及多个代码包，同一个代码包也可能被多个阶段复用。

| 阶段文档 | 主要代码包 | 说明 |
|----------|------------|------|
| `01-context-builder.md` | `task/`、`context/` | 任务契约、状态摘要和上下文构造 |
| `02-memory-state.md` | `memory/`、`task/`、`artifact/`、`context/` | 记忆、状态和产物边界 |
| `03-checkpoint-resume.md` | `observability/checkpoint/`、`execution/`、`task/` | checkpoint、step runner 和恢复语义 |
| `04-schema-artifact.md` | `artifact/`、`scenarios/research_mini/schemas.py` | Runtime 只提供 artifact 记录和 store，具体 schema 属于场景 |
| `05-trace-replay.md` | `observability/trace/` | JSONL trace、读取、复盘和脱敏 |
| `06-minimal-runtime.md` | `execution/`、`scenarios/research_mini/` | 最小 Runtime 串联、工具策略和具体场景 |
| `07-code-review-mini.md` | `execution/`、`scenarios/code_review_mini/` | 代码审查场景驱动 Runtime Core 复用 |
| `08-workflow-agent-selection.md` | 场景设计前置判断 | 判断任务应采用 workflow、agentic workflow 还是 autonomous agent |

因此，后续阅读时应先按阶段文档理解能力，再按代码包查看实现边界。

非功能能力总览：[agent-non-functional-capabilities-overview.md](docs/agent-non-functional-capabilities-overview.md)。
架构边界文档：[runtime-core-architecture.md](docs/runtime-core-architecture.md)。

## 阶段能力文档

| 阶段 | 能力 | 状态 | 说明文档 |
|------|------|------|----------|
| 1 | Context Builder | completed | [01-context-builder.md](docs/01-context-builder.md) |
| 2 | Memory / State 分层 | completed | [02-memory-state.md](docs/02-memory-state.md) |
| 3 | Checkpoint / Resume | completed | [03-checkpoint-resume.md](docs/03-checkpoint-resume.md) |
| 4 | Schema Artifact 交接 | completed | [04-schema-artifact.md](docs/04-schema-artifact.md) |
| 5 | Trace 与复盘 | completed | [05-trace-replay.md](docs/05-trace-replay.md) |
| 6 | 最小 Runtime 串联 | completed | [06-minimal-runtime.md](docs/06-minimal-runtime.md) |
| 7 | code_review_mini 场景试验 | completed | [07-code-review-mini.md](docs/07-code-review-mini.md) |
| 8 | Workflow / Agent 选择策略 | completed | [08-workflow-agent-selection.md](docs/08-workflow-agent-selection.md) |

## Public API 使用约定

场景代码、脚本和外部测试优先使用包级导入：

```python
from runtime_core.task import TaskContract, RuntimeState
from runtime_core.context import ContextBuilder, ContextPolicy
from runtime_core.memory import MemoryRecord, MemoryStore
from runtime_core.artifact import ArtifactRecord, ArtifactStore
from runtime_core.execution import MinimalRuntime, ToolPolicyChecker
from runtime_core.observability import TraceRecorder, FileCheckpointStore
```

深层模块路径主要用于包内部实现。依赖边界由 `tests/test_runtime_core_boundaries.py` 做轻量检查，防止后续把具体 scenario 反向带入 `runtime_core/`。

## 建议阅读顺序

1. 先读本文，理解项目范围和当前进度。
2. 阅读 [agent-non-functional-capabilities-overview.md](docs/agent-non-functional-capabilities-overview.md)，理解 Agent 系统非功能能力总览。
3. 阅读 [01-context-builder.md](docs/01-context-builder.md)，理解已完成的 Context Builder。
4. 阅读 [02-memory-state.md](docs/02-memory-state.md)，理解已完成的 Memory / State 分层边界。
5. 阅读 [03-checkpoint-resume.md](docs/03-checkpoint-resume.md)，理解已完成的 checkpoint / resume 语义。
6. 阅读 [04-schema-artifact.md](docs/04-schema-artifact.md)，理解已完成的 schema artifact 交接。
7. 阅读 [05-trace-replay.md](docs/05-trace-replay.md)，理解已完成的 trace 与复盘语义。
8. 阅读 [06-minimal-runtime.md](docs/06-minimal-runtime.md)，理解已完成的最小 Runtime 串联。
9. 查看 `scripts/run_context_demo.py`，观察阶段 1 如何运行。
10. 查看 `scripts/run_memory_state_demo.py`，观察阶段 2 如何区分 memory、state 和 artifact。
11. 查看 `scripts/run_resume_demo.py`，观察阶段 3 如何从 checkpoint 恢复。
12. 查看 `scripts/run_artifact_handoff_demo.py`，观察阶段 4 如何通过 schema artifact 交接。
13. 查看 `scripts/run_trace_demo.py`，观察阶段 5 如何记录和复盘 trace。
13. 查看 `scripts/run_research_mini.py`，观察阶段 6 如何串联完整流程。
14. 查看 `tests/`，理解阶段 1-6 的验收规则。

## 与计划意图的关系

本项目是 `Agent 核心能力小步验证开发计划` 的代码承载区。README 只保留全局导航和阶段总览；六个阶段能力的概念、设计和说明放在 `docs/` 下，避免 README 变成过长的实现说明。

当前阶段主要验证：

- 上下文不是完整聊天历史，而是当前 step 的工作视图。
- Step 之间应优先通过可校验 artifact 交接，而不是自由文本。
- 失败后应能通过 trace 定位 step、artifact、工具和人工介入原因。
- Runtime Core 应支撑具体场景运行，但不把场景业务逻辑吸收到核心模块里。
- Runtime Core 应先保持小核心，不急于插件化和平台化。
- 每个阶段都要有脚本、测试和计划状态记录。
