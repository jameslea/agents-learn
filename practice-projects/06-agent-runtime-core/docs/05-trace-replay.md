# 阶段 5：Trace 与复盘

## 目录

- [能力定位](#能力定位)
- [当前状态](#当前状态)
- [实现文件](#实现文件)
- [核心对象](#核心对象)
- [事件类型](#事件类型)
- [最小场景](#最小场景)
- [复盘语义](#复盘语义)
- [脱敏策略](#脱敏策略)
- [验证方式](#验证方式)
- [Demo 输出说明](#demo-输出说明)
- [核心概念](#核心概念)
- [经验教训](#经验教训)
- [当前边界](#当前边界)

## 能力定位

Trace 要解决的是失败后的复盘问题：

```text
是哪一步失败？
输入摘要是什么？
调用了什么工具？
生成或消费了什么 artifact？
为什么进入 failed 或 human_required？
```

Trace 不是普通日志，也不是评测结果。它应记录足以复盘的关键 runtime 事件，同时避免过载和泄露敏感信息。

## 当前状态

状态：`completed`

阶段 5 已新增本地 JSONL trace 能力，并通过 demo 验证：

- 事件写入。
- 事件读取。
- 失败 step 复盘。
- artifact created / consumed 流转复盘。
- medium / high 风险事件复盘。
- human required 事件复盘。
- 基础敏感字段脱敏。

## 实现文件

相对代码根目录：`practice-projects/06-agent-runtime-core/`

```text
runtime_core/observability/trace/
scripts/run_trace_demo.py
tests/test_trace_replay.py
```

## 核心对象

| 对象 | 职责 |
|------|------|
| `TraceEventType` | 枚举 runtime 关键事件类型 |
| `TraceEvent` | 一条可复盘事件，包含 task、step、summary、data、risk 和 recoverable |
| `TraceRecorder` | 写入 JSONL trace，并在写入前做基础脱敏 |
| `TraceReader` | 从 JSONL 文件读取事件 |
| `TraceReplaySummary` | 汇总失败 step、artifact 流转、风险事件和人工介入事件 |

## 事件类型

| 事件 | 内容 |
|------|------|
| `task_started` | task_id、task_type、goal summary |
| `task_finished` | final status、summary |
| `step_started` | step_id、input summary、time |
| `step_passed` | step_id、output summary、time |
| `step_failed` | error type、message、recoverable、risk |
| `artifact_created` | artifact id、type、schema、path |
| `artifact_consumed` | artifact id、schema、consumer step |
| `tool_called` | tool、args summary、risk |
| `human_required` | reason、risk、pending action |

## 最小场景

```text
task_started
research step_started
artifact_created
research step_passed
writer step_started
artifact_consumed
tool_called
writer step_failed
human_required
task_finished
```

demo 会故意触发 writer 失败，用于验证 trace 是否能定位失败 step、错误原因和后续人工介入。

## 复盘语义

`TraceReader.replay()` 当前生成四类摘要：

- `failed_steps`：哪些 step 失败、失败摘要、错误数据、是否可恢复。
- `artifact_flow`：artifact 创建和消费事件，观察上下游交接关系。
- `risk_events`：medium / high 风险事件，例如工具调用或失败事件。
- `human_required`：需要人工介入的事件。

这些摘要不是最终报告，而是“失败后快速定位问题”的最小复盘视图。

## 脱敏策略

`TraceRecorder` 写入前会对以下字段做基础脱敏：

- key 中包含 `api_key`
- key 中包含 `token`
- key 中包含 `password`
- key 中包含 `secret`
- key 中包含 `credential`

字符串中形如 `token=...`、`password=...` 的片段也会替换为 `[REDACTED]`。

当前脱敏是最小实现，只覆盖常见字段和简单内联片段。真实系统还需要更完整的 secret scanner、allowlist / denylist 和审计策略。

## 验证方式

运行 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_trace_demo.py
```

输出 JSON：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_trace_demo.py --format json
```

运行测试：

```bash
python3 -m pytest practice-projects/06-agent-runtime-core/tests/test_trace_replay.py
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

## Demo 输出说明

demo 输出包含：

- trace 文件路径。
- event count 和事件类型统计。
- failed step 摘要。
- artifact created / consumed 流转。
- 风险事件和人工介入事件。

典型失败摘要：

```text
writer | Writer failed because required section was missing. token=[REDACTED] | recoverable=True
```

## 核心概念

- Trace 记录的是 runtime 关键事件，不是完整日志、完整上下文或完整产物。
- 每个事件应能关联 `task_id`，必要时关联 `step_id`。
- artifact 进入 trace 时应记录 id、schema、path 等引用信息，不记录完整 payload。
- tool call 进入 trace 时应记录工具名、参数摘要和风险等级，不记录密钥或完整敏感参数。
- 失败事件需要记录 recoverable，方便后续决定 retry、blocked 或 human required。

## 经验教训

- 没有 trace 时，失败后只能看到最终错误；有事件链后，可以定位到 step、artifact 和工具层面。
- trace 太细会变成噪声和泄露风险，太粗又无法复盘；当前先记录关键事件和摘要。
- 脱敏应该发生在写入前，而不是读出后，否则敏感信息已经落盘。
- 阶段 5 先显式记录 trace，不强行侵入 StepRunner 和 ArtifactStore；阶段 6 再统一串联更稳。

## 当前边界

本阶段不做：

- Langfuse / LangSmith / Phoenix 集成。
- 可视化 trace UI。
- 分布式链路追踪。
- 长期 trace 仓库。
- 完整 secret scanner。
- 自动接入所有 step runner 和 artifact store 操作。

先用本地 JSONL 验证 trace 语义。
