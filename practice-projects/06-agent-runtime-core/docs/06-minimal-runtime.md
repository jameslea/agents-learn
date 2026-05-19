# 阶段 6：最小 Runtime 串联

## 能力定位

最小 Runtime 串联要把前五个阶段的能力组合成一个可运行的小型 Agent 场景。

目标不是做完整框架，而是验证这些公共能力能否支撑真实流程：

```text
contract -> state -> context -> step -> artifact -> trace -> resume / blocked
```

## 当前状态

状态：`pending`

当前只完成阶段 1。阶段 2-5 完成后，才能进入完整串联。

## 推荐场景

优先使用 `research_mini`：

```text
给定一个主题，
生成 research plan，
整理 evidence table，
生成短报告，
评审并输出 review result。
```

这个场景足够具体，又不会像代码执行或运维自愈那样过早引入高风险工具。

## 计划实现

预计新增：

```text
runtime_core/step_runner.py
scenarios/research_mini/
scripts/run_research_mini.py
tests/test_minimal_runtime.py
```

## 需要串联的能力

| 能力 | 串联方式 |
|------|----------|
| TaskContract | 明确任务目标、输入、期望产物 |
| RuntimeState | 记录当前 step 和执行进度 |
| ContextBuilder | 为每个 step 构造工作视图 |
| MemoryRecord | 提供项目偏好和可复用经验 |
| Artifact | 在 step 之间结构化交接 |
| Trace | 记录关键事件和失败原因 |
| Checkpoint | 中断后恢复 |
| Blocked | 无法自动继续时停下来 |

## 横向治理约束

最小 Runtime 应至少演示：

- 工具策略：工具声明风险等级、只读属性、是否需要审批。
- 预算与延迟：记录 step 开始时间、结束时间、调用次数。
- blocked 终态：工具越权、schema 不合格、预算超限或重复失败时停止。

## 验收标准

- 一个命令可运行完整流程。
- 支持中断后恢复。
- 每个 step 有 artifact 或 trace。
- 最终输出包括 report、review result、trace summary。
- 至少有一个 blocked 演示样例。

## 当前边界

本阶段仍不做：

- Web UI。
- 插件市场。
- 多租户权限系统。
- 复杂多 Agent。
- 企业级部署。

这一步的目标是证明 Runtime Core 小核心可以支撑一个真实但有限的 Agent 流程。
