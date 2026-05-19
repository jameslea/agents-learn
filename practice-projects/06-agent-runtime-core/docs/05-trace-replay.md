# 阶段 5：Trace 与复盘

## 能力定位

Trace 要解决的是失败后的复盘问题：

```text
是哪一步失败？
输入是什么？
调用了什么工具？
生成了什么 artifact？
为什么进入 blocked 或 failed？
```

Trace 不是普通日志。它应记录足以复盘的关键事件，同时避免过载和泄露敏感信息。

## 当前状态

状态：`pending`

当前阶段 1 只有 `selection_log`，它能解释 Context Builder 的选择过程，但还不是完整 Runtime trace。

## 计划实现

预计新增：

```text
runtime_core/trace.py
scripts/run_trace_demo.py
tests/test_trace_replay.py
```

## 建议事件

| Trace 事件 | 内容 |
|------------|------|
| `task_started` | task_id、task_type、goal summary |
| `step_started` | step_id、input summary、time |
| `step_finished` | step_id、output summary、time |
| `step_failed` | error type、message、recoverable |
| `artifact_created` | artifact id、schema、path |
| `tool_called` | tool、args summary、risk |
| `human_required` | reason、risk、pending action |
| `task_finished` | final status、summary |

## 需要验证的问题

- trace 是否足以定位失败原因。
- trace 是否不会记录完整上下文原文。
- trace 是否不会泄露 API key、凭证、敏感文件内容。
- trace 是否可以和 state、artifact 关联。

## 验收标准

- 每次 demo 运行生成 JSONL trace。
- 失败时能根据 trace 定位 step 和原因。
- trace 中记录 artifact 引用，而不是完整产物正文。

## 当前边界

本阶段不做：

- Langfuse / LangSmith / Phoenix 集成。
- 可视化 trace UI。
- 分布式链路追踪。
- 长期 trace 仓库。

先用本地 JSONL 验证 trace 语义。
