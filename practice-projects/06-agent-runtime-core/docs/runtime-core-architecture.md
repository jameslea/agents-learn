# Runtime Core 架构说明

## 目录

- [定位](#定位)
- [六个核心包](#六个核心包)
- [公开 API](#公开-api)
- [依赖边界](#依赖边界)
- [场景代码如何复用](#场景代码如何复用)
- [当前验证](#当前验证)

## 定位

`runtime_core/` 是跨 Agent 场景复用的小核心。它不负责具体业务推理，也不负责构建通用平台，而是提供 Agent 运行时反复需要的公共支撑：

```text
task -> context -> memory -> artifact -> execution -> observability
```

业务 Agent 应放在 `scenarios/` 中。Runtime Core 只保存可复用的任务契约、上下文构造、记忆记录、结构化产物、执行控制和可观测能力。

## 六个核心包

| 包 | 职责 | 不负责 |
|----|------|--------|
| `task` | 定义 `TaskContract`、`RuntimeState`、step 状态 | 不保存长期记忆，不保存完整 artifact payload 历史 |
| `context` | 构造当前 step 的 `ContextBundle`，解释上下文选择原因 | 不做业务决策，不直接执行工具 |
| `memory` | 管理跨任务可复用的 `MemoryRecord`、写入 gate、检索规则 | 不保存当前任务进度，不替代 checkpoint |
| `artifact` | 保存和校验结构化产物，支持 schema artifact 交接 | 不内置具体业务 schema |
| `execution` | 串联 step、工具策略和最小 Runtime | 不把具体场景 step 写进 core |
| `observability` | 提供 checkpoint、trace、replay 和基础脱敏 | 不反向驱动业务流程，不替代评估系统 |

## 公开 API

外部代码优先使用包级导入：

```python
from runtime_core.task import TaskContract, RuntimeState
from runtime_core.context import ContextBuilder, ContextPolicy
from runtime_core.memory import MemoryRecord, MemoryStore
from runtime_core.artifact import ArtifactRecord, ArtifactStore
from runtime_core.execution import MinimalRuntime, ToolPolicyChecker
from runtime_core.observability import FileCheckpointStore, TraceRecorder
```

深层模块主要服务包内部组织。场景代码、demo 脚本和测试应尽量依赖包级 API，避免直接绑定内部文件路径。

## 依赖边界

当前允许的 Runtime Core 内部依赖方向如下：

| 包 | 允许依赖 |
|----|----------|
| `task` | `task` |
| `memory` | `memory`、`context` |
| `artifact` | `artifact`、`context` |
| `context` | `context`、`task`、`memory`、`artifact` |
| `observability` | `observability`、`task` |
| `execution` | `execution`、`task`、`context`、`memory`、`artifact`、`observability` |

这组规则表达的是职责方向：

- `task` 是基础契约层，不能反向依赖其他 Runtime 能力。
- `context` 可以读取 task、memory、artifact 的摘要，用来构造工作视图。
- `memory` 和 `artifact` 允许提供 `to_candidate()` 这类上下文适配方法，但不能依赖 execution。
- `observability` 可以记录和恢复 state，但不能依赖 context、memory、artifact 或 execution。
- `execution` 是组合层，可以串联其他核心能力。
- `runtime_core` 不能依赖 `scenarios`，否则公共核心会被具体业务污染。

这些规则已经通过 `tests/test_runtime_core_boundaries.py` 做轻量检查。

## 场景代码如何复用

一个具体 Agent 场景建议按下面方式组织：

```text
scenarios/<agent_name>/
  schemas.py     # 场景自己的 artifact schema
  scenario.py    # 业务 step 和运行流程
```

推荐做法：

- 用 `TaskContract` 表达任务入口。
- 用 `MinimalRuntime` 或更薄的 `StepRunner` 串联流程。
- 每个 step 只读取当前 `ContextBundle` 和上游 schema artifact。
- 下游 step 通过 `ArtifactStore` 消费 artifact，而不是解析自由文本。
- 高风险工具调用先经过 `ToolPolicyChecker`。
- 失败时写入 trace，必要时进入 blocked，而不是无限 retry。

不推荐做法：

- 在 `runtime_core/` 中写具体业务 step。
- 在场景代码中直接依赖 Runtime Core 的内部 rule 函数。
- 把完整聊天历史、完整 trace 或完整 artifact payload 塞进 context。
- 让 memory、artifact 或 trace 互相替代。

## 当前验证

当前使用 `research_mini` 场景验证这个结构：

```text
plan_research
collect_evidence -> EvidenceTable
write_report -> DraftReport
review_report -> ReviewResult
```

该场景已经覆盖：

- 任务契约和运行状态。
- Context Builder。
- Memory / State / Artifact 分层。
- Schema Artifact 交接。
- Checkpoint / Resume。
- Trace / Replay。
- Tool Policy 和 blocked 示例。

因此当前目录结构可以先稳定下来。后续新增能力应优先放入现有六个包；只有当能力确实无法归类时，才考虑新增一级包。
