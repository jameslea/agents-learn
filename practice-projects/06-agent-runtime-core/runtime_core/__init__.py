"""Agent Runtime Core 的独立小核心。

这个包从干净目录重新开始，只放跨 Agent 可复用的 Runtime 基础能力。
当前阶段包含：

- contracts：任务入口契约。
- state：任务步骤状态。
- context：Context Builder 和 ContextBundle。

后续阶段会继续加入 memory、artifact、trace 和 step runner。
"""
