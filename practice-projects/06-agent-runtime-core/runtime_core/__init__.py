"""Agent Runtime Core 的独立小核心。

这个包从干净目录重新开始，只放跨 Agent 可复用的 Runtime 基础能力。
当前阶段包含：

- context：Context Builder 和 ContextBundle。
- memory：跨任务可复用记忆。
- artifact：结构化产物记录、保存和 schema 校验。
- task：任务入口契约、任务步骤状态和 RuntimeState。
- execution：顺序 step 执行、工具策略检查和最小 Runtime 串联器。
- observability：checkpoint、JSONL trace 和复盘能力。

后续阶段会继续加入更完整的 runtime 编排。
"""
