# Agent Runtime Core 小步验证项目

## 项目定位

本项目用于验证 Agent Runtime 的核心公共能力。当前阶段不追求完整生产级 Runtime，而是围绕上下文、状态、记忆、产物、trace 和可恢复执行做小步验证。

对应计划文档：[docs/agent-core-capabilities-validation-plan.md](../../docs/agent-core-capabilities-validation-plan.md)。

## 当前进度

阶段 1：Context Builder 已完成最小验证。
阶段 2：Memory / State 分层已完成最小验证。

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
- 可见性、信任等级、敏感候选拦截和 required context 检查。
- 可运行 demo 和测试。

尚未实现：

- 持久化 memory store。
- artifact schema 验证 / store。
- checkpoint / resume。
- JSONL trace recorder。
- StepRunner。
- tool policy、budget、latency、blocked 终态。
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
  runtime_core/
    __init__.py
    artifact.py
    contracts.py
    state.py
    context.py
    memory.py
  scripts/
    run_context_demo.py
    run_memory_state_demo.py
  tests/
    conftest.py
    test_context_builder.py
    test_memory_state_boundaries.py
```

## 阶段能力文档

| 阶段 | 能力 | 状态 | 说明文档 |
|------|------|------|----------|
| 1 | Context Builder | completed | [01-context-builder.md](docs/01-context-builder.md) |
| 2 | Memory / State 分层 | completed | [02-memory-state.md](docs/02-memory-state.md) |
| 3 | Checkpoint / Resume | pending | [03-checkpoint-resume.md](docs/03-checkpoint-resume.md) |
| 4 | Schema Artifact 交接 | pending | [04-schema-artifact.md](docs/04-schema-artifact.md) |
| 5 | Trace 与复盘 | pending | [05-trace-replay.md](docs/05-trace-replay.md) |
| 6 | 最小 Runtime 串联 | pending | [06-minimal-runtime.md](docs/06-minimal-runtime.md) |

## 建议阅读顺序

1. 先读本文，理解项目范围和当前进度。
2. 阅读 [01-context-builder.md](docs/01-context-builder.md)，理解已完成的 Context Builder。
3. 阅读 [02-memory-state.md](docs/02-memory-state.md)，理解已完成的 Memory / State 分层边界。
4. 按阶段顺序阅读后续能力文档，理解计划如何逐步推进。
5. 查看 `scripts/run_context_demo.py`，观察阶段 1 如何运行。
6. 查看 `scripts/run_memory_state_demo.py`，观察阶段 2 如何区分 memory、state 和 artifact。
7. 查看 `tests/`，理解阶段 1 和阶段 2 的验收规则。

## 与计划意图的关系

本项目是 `Agent 核心能力小步验证开发计划` 的代码承载区。README 只保留全局导航和阶段总览；六个阶段能力的概念、设计和说明放在 `docs/` 下，避免 README 变成过长的实现说明。

当前阶段主要验证：

- 上下文不是完整聊天历史，而是当前 step 的工作视图。
- Runtime Core 应先保持小核心，不急于插件化和平台化。
- 每个阶段都要有脚本、测试和计划状态记录。
