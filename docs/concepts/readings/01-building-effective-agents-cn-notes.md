# 中文导读：Anthropic Building Effective Agents

> 原文：[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
>
> 发布者：Anthropic
>
> 发布时间：2024-12
>
> 资料形态：工程文章
>
> 阅读优先级：必读

## 这篇资料解决什么问题

这篇文章讨论的不是某个具体框架，也不是某种 prompt 技巧，而是一个更基础的问题：

```text
在真实工程中，应该如何构建有效的 Agent 系统？
```

它的核心价值在于把 Agent 开发从“让模型更自主”拉回到工程判断：

- 什么时候不需要 Agent，只需要普通 workflow。
- 什么时候需要让模型动态决定下一步。
- 复杂任务应如何拆成更小、更可靠的模式。
- 工具接口、环境反馈、停止条件和可观察性为什么重要。

这和当前项目的 Runtime Core 探索高度相关。我们之前已经发现，Agent 系统真正困难的地方不只是模型回答，而是上下文、状态、工具、artifact、trace、权限、失败处理和人类介入。这篇文章提供了一个很好的上层判断框架：不要先追求“完美自主 Agent”，而是先构造可控、可组合、可观测的执行结构。

## 核心概念

### Workflow 与 Agent 的区别

文章最重要的区分是 workflow 和 agent。

Workflow 是预先写好的控制流。模型可能参与其中，但执行路径主要由代码决定。例如：

```text
输入 -> 模型处理 -> 工具执行 -> 模型总结 -> 输出
```

Agent 则更开放。模型会根据上下文、工具结果和环境反馈，自主决定下一步行动。例如：

```text
目标 -> 模型判断下一步 -> 工具调用 -> 观察结果 -> 模型重新判断 -> 继续或停止
```

这个区分非常关键。很多任务并不需要完全自主 Agent。对生产系统来说，workflow 往往更可控、更容易测试、更容易复盘。Agent 应该用于那些路径难以预先穷举、需要动态判断和多步反馈的任务。

### 从简单模式开始

文章强调，构建 Agent 系统时应优先使用简单、可组合的模式，而不是一开始就做大而全的通用框架。

常见模式包括：

| 模式 | 中文理解 | 适用场景 |
|------|----------|----------|
| Prompt Chaining | 提示链 | 把复杂任务拆成多个顺序步骤，每一步产出进入下一步。 |
| Routing | 路由 | 根据输入类型、任务难度或风险选择不同处理路径。 |
| Parallelization | 并行化 | 将任务拆成多个可并行判断或生成的子任务。 |
| Orchestrator-Workers | 编排者-工作者 | 一个模型或控制器分解任务，多个 worker 执行子任务。 |
| Evaluator-Optimizer | 评估者-优化者 | 一个组件生成结果，另一个组件评估并推动改进。 |

这些模式比“创建更多角色”更重要。角色只是表层命名，真正决定系统质量的是任务如何分解、状态如何传递、产物如何校验、失败如何处理。

### 工具接口决定 Agent 能力边界

文章特别强调工具和环境接口。一个 Agent 是否可靠，不只取决于模型能力，也取决于它能看到什么、能调用什么、工具返回什么、错误如何表达。

这和 SWE-agent 中的 Agent-Computer Interface 视角是一致的。对代码类 Agent 来说，shell、文件系统、测试命令、错误输出、diff、搜索工具，都是 Agent 能力的一部分。接口设计不好，模型再强也会被迫猜测。

对当前项目来说，这直接对应 Runtime Core 中的：

- Tool Policy。
- Tool Call Trace。
- Artifact Schema。
- Context Builder。
- Blocked 状态。
- Checkpoint / Resume。

### 可观察性比“看起来聪明”更重要

文章的实践倾向是：让系统的关键决策和中间过程可观察。Agent 系统如果只有最终答案，就很难知道失败原因。

一个可维护的 Agent 至少应回答：

- 当前任务目标是什么？
- 当前 step 是什么？
- 模型看到了哪些上下文？
- 调用了哪些工具？
- 工具返回了什么？
- 为什么继续、停止或进入 blocked？
- 中间 artifact 是否有效？

这正是当前 Runtime Core 中 Trace / Replay 文档所关注的问题。

## 关键术语

| 英文术语 | 中文理解 | 对当前项目的意义 |
|----------|----------|------------------|
| Workflow | 工作流 / 固定控制流 | 路径由代码控制，适合稳定任务。 |
| Agent | 智能体 / 动态控制循环 | 模型根据反馈决定下一步，适合开放任务。 |
| Prompt Chaining | 提示链 | 对应多 step 顺序执行和 artifact 传递。 |
| Routing | 路由 | 对应按任务类型、风险或成本选择不同策略。 |
| Parallelization | 并行化 | 对应多个候选、多个检查器或多个 worker。 |
| Orchestrator-Workers | 编排者-工作者 | 对应上层任务拆解和下层子任务执行。 |
| Evaluator-Optimizer | 评估者-优化者 | 对应生成、校验、修正循环。 |
| Tool Use | 工具使用 | 对应 Tool schema、权限、安全边界和 trace。 |
| Agent-Computer Interface | Agent-计算机接口 | 对应工具和环境如何暴露给 Agent。 |
| Observability | 可观测性 | 对应 trace、日志、artifact、评估和复盘。 |

## 最值得精读的部分

这篇文章不需要逐字翻译，但下面几部分值得精读：

1. Workflow 与 Agent 的区别。

   这是后续判断“是否真的需要 Agent”的基础。当前项目从 D-lite 到 Runtime Core 的经验也说明，很多场景先用 workflow 更稳。

2. 几种常见 Agentic Workflow 模式。

   Prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer 都可以直接转化为工程结构。后续做场景试验时，可以优先使用这些模式，而不是直接做通用自主 Agent。

3. 工具和环境接口的设计原则。

   这部分和 Runtime Core 的 Tool Policy、Trace、Artifact、Context Builder 关系很大。工具接口如果不清晰，Agent 行为就会变得不可控。

4. 简单系统优先的工程判断。

   文章反复传达一个倾向：先构建能工作的简单系统，再逐步增加复杂度。这对当前项目尤其重要，因为我们已经感受到 Runtime Core 过度抽象会增加复杂度。

## 和当前项目的关系

这篇文章可以重新校准我们对 Runtime Core 的定位。

当前项目已经形成的判断是：

```text
Runtime Core 不是要替代具体 Agent，
而是为不同 Agent 场景提供公共运行支撑。
```

Anthropic 这篇文章进一步说明，公共支撑不应该一开始做成大而全的自治框架，而应该围绕稳定模式逐步提取：

| Anthropic 观点 | 当前项目对应 |
|----------------|--------------|
| Workflow 通常比全自主 Agent 更稳 | Code Review Mini 采用明确 step 串联，而不是自由循环。 |
| Agent 适合动态、多步、反馈驱动任务 | D-lite 的修复循环、后续可恢复任务可以引入更强动态性。 |
| 工具接口决定能力边界 | Runtime Core 的 Tool Policy 和 Tool Trace 是必要公共能力。 |
| 中间过程需要可观察 | Trace / Replay 是生产级 Agent 的基础。 |
| 从简单模式开始 | Runtime Core 应保持小核心，不急于插件化和平台化。 |

它也帮助解释我们之前遇到的一个问题：为什么有些项目一开始做得太“Agent 化”反而效果不好。原因不是 Agent 思想错误，而是任务边界、工具接口、状态、trace、评估和失败处理没有跟上。

## 可以转化为实践的点

### 1. 在每个新场景开始前先判断 workflow 还是 agent

后续设计新场景时，可以先写一个小表：

| 判断问题 | 如果答案是“是” | 倾向 |
|----------|----------------|------|
| 执行路径是否稳定？ | 是 | Workflow |
| 是否需要模型根据反馈选择下一步？ | 是 | Agent |
| 是否有高风险工具调用？ | 是 | Workflow + Guardrails |
| 是否需要多轮尝试和恢复？ | 是 | Agent + Checkpoint |
| 是否需要多人或多角色协作？ | 不一定 | 先考虑 Orchestrator-Workers |

这个判断可以避免过早引入自主循环。

### 2. 把 Runtime Core 的能力映射到常见模式

当前 Runtime Core 可以继续围绕这些模式验证：

| 模式 | Runtime Core 需要支持的能力 |
|------|-----------------------------|
| Prompt Chaining | Step、Artifact、Context Builder |
| Routing | TaskContract、Policy、RuntimeState |
| Parallelization | 多 Artifact、多个 step result、trace 分支 |
| Orchestrator-Workers | 结构化 handoff、worker artifact、统一 trace |
| Evaluator-Optimizer | Evaluation artifact、retry budget、blocked reason |

这样 Runtime Core 就不是抽象堆砌，而是从真实 workflow / agentic workflow 中提取公共能力。

### 3. 工具接口需要从一开始设计

每个工具至少应明确：

- 工具做什么。
- 输入 schema 是什么。
- 输出 schema 是什么。
- 是否有副作用。
- 需要什么权限。
- 失败如何表达。
- 返回结果是否进入 Context、Artifact、Memory 或 Trace。

这可以成为后续 Tool Policy 文档和代码改进的检查表。

### 4. Trace 应记录关键决策，而不是所有文本

Trace 的目标不是把所有上下文和所有模型输出都塞进去，而是记录足以复盘的结构化信息：

- step started / completed / failed / blocked。
- selected context source。
- tool call and result。
- artifact created / validated。
- retry reason。
- human intervention。
- final outcome。

这与 Anthropic 强调的可观察性一致。

## 不需要深读的部分

这篇文章中有些部分对当前阶段不是最高优先级：

- 不需要马上照搬所有 workflow 模式。
- 不需要立即实现复杂并行、多 worker 或 evaluator-optimizer 框架。
- 不需要把文章中的所有模式都做成 Runtime Core 抽象。
- 不需要过早做通用 Agent 平台。

当前更重要的是把文章中的方法论用于判断：

```text
什么时候用 workflow，
什么时候用 agent，
哪些公共能力值得从业务代码中提取出来。
```

## 阶段性结论

这篇文章对当前项目最重要的启发是：

```text
有效 Agent 系统不是越自主越好，
而是要在任务边界、工具接口、状态、产物、trace 和评估之间取得平衡。
```

从这个角度看，当前 Runtime Core 的方向是合理的，但需要保持克制。它不应该一开始追求通用大框架，而应该继续围绕具体场景小步验证：

- Context 如何构造。
- Memory 如何使用。
- Checkpoint 如何恢复。
- Artifact 如何交接。
- Trace 如何复盘。
- Tool Policy 如何控制风险。

只有这些公共能力在多个场景中反复出现，并且确实降低了业务代码复杂度，才值得继续沉淀为 Runtime Core。

## 后续阅读动作

建议下一步按阅读路线继续创建：

```text
docs/concepts/readings/02-openai-practical-guide-to-building-agents-cn-notes.md
```

但在进入下一篇之前，可以先把本文中的两个判断用于回看当前项目：

- Code Review Mini 更像 workflow，还是 agent？
- Runtime Core 当前已经支持哪些 Anthropic 提到的 workflow / agentic workflow 模式？
