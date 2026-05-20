# Workflow / Agent 选择策略

## 目录

- [能力定位](#能力定位)
- [为什么这是先决条件](#为什么这是先决条件)
- [Workflow 与 Agent 的边界](#workflow-与-agent-的边界)
  - [Workflow](#workflow)
  - [Agent](#agent)
  - [Agentic Workflow](#agentic-workflow)
- [常见模式](#常见模式)
  - [Prompt Chaining](#prompt-chaining)
  - [Routing](#routing)
  - [Parallelization](#parallelization)
  - [Orchestrator-Workers](#orchestrator-workers)
  - [Evaluator-Optimizer](#evaluator-optimizer)
  - [Autonomous Agent](#autonomous-agent)
- [选择策略](#选择策略)
  - [第一层：先判断路径稳定性](#第一层先判断路径稳定性)
  - [第二层：再判断风险和控制要求](#第二层再判断风险和控制要求)
  - [第三层：选择具体模式](#第三层选择具体模式)
  - [第四层：决定 Runtime Core 介入深度](#第四层决定-runtime-core-介入深度)
- [Runtime Core 的角色](#runtime-core-的角色)
- [当前场景回看](#当前场景回看)
  - [research_mini](#research_mini)
  - [code_review_mini](#code_review_mini)
  - [D-lite 的启发](#d-lite-的启发)
- [后续场景设计检查表](#后续场景设计检查表)
- [经验教训](#经验教训)
- [当前边界](#当前边界)

## 能力定位

本文不是一个新的 Runtime Core 代码阶段，而是一个**场景设计前置判断文档**。

它要回答的问题是：

```text
在开始设计一个 Agent 系统之前，
这个任务应该被做成 workflow，还是 agent？
如果不是完全自主 agent，又应该选择哪种 agentic workflow 模式？
Runtime Core 应该支撑什么，而不应该替代什么？
```

这个判断来自 Anthropic 的 [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 对 workflow 和 agent 的区分，也来自当前项目在 D-lite、Runtime Core、research_mini 和 code_review_mini 中的实践经验。

## 为什么这是先决条件

Agent 系统是否能成功，往往不是从模型调用那一刻才决定的，而是在更早的设计阶段就已经被决定了。

如果一个路径稳定、输入输出明确、风险较高的任务被误设计成“完全自主 Agent”，常见结果是：

- 控制流不可预测。
- 调试和复盘困难。
- 工具权限难以约束。
- 成本和延迟失控。
- 失败后不知道应该重试、停止还是人工介入。

反过来，如果一个开放、长程、反馈驱动的任务被硬塞进固定 workflow，常见结果是：

- 无法处理分支情况。
- 遇到异常只能失败，不能调整计划。
- 每个边界条件都需要手写规则。
- 系统变成复杂但不智能的流程脚本。

因此，在引入 Runtime Core 之前，应先做一层选择：

```text
任务形态判断
  -> 模式选择
  -> Runtime Core 能力选择
  -> 场景实现
```

这也是当前 Runtime Core 继续演进时最重要的约束：Runtime Core 不应该推动所有场景都变成自主 Agent，而应该支持不同层次的 workflow / agentic workflow。

## Workflow 与 Agent 的边界

### Workflow

Workflow 是预先定义控制流的任务执行方式。模型可以参与其中，但路径主要由代码和规则控制。

典型结构：

```text
输入
  -> step 1
  -> step 2
  -> step 3
  -> 输出
```

适合场景：

- 步骤稳定。
- 输入输出明确。
- 成功标准清楚。
- 工具风险较高，需要严格控制。
- 需要可测试、可复盘、可回归。

Workflow 的优势是可控、可测、易复盘。缺点是灵活性有限，遇到新分支时需要扩展流程。

### Agent

Agent 是模型根据目标、上下文、工具结果和环境反馈动态决定下一步行动的执行方式。

典型结构：

```text
目标
  -> 模型判断下一步
  -> 工具调用
  -> 观察结果
  -> 模型重新判断
  -> 继续 / 停止 / blocked
```

适合场景：

- 路径难以预先穷举。
- 需要根据环境反馈调整行动。
- 任务较长，存在多轮尝试。
- 需要探索、搜索、诊断或修复。
- 中间状态和失败原因需要被持续吸收。

Agent 的优势是灵活、能处理开放任务。缺点是可预测性差，对状态、工具、trace、权限和停止条件要求更高。

### Agentic Workflow

很多真实系统并不属于纯 workflow 或纯 agent，而是介于两者之间。

更实际的形态是：

```text
外层 workflow 控制任务边界，
局部 step 使用 LLM 或 agentic pattern 做动态判断。
```

例如 code_review_mini 当前是一个 workflow：

```text
collect_code_context -> llm_or_rule_review -> propose_patch
```

但其中 `llm_or_rule_review` 可以使用真实 LLM，并根据 schema 校验、失败原因和风险等级产生不同后续处理。它不是完全自主 Agent，但已经具备局部 agentic 能力。

## 常见模式

### Prompt Chaining

中文理解：提示链 / 顺序加工链。

结构：

```text
step A -> artifact A
step B consumes artifact A -> artifact B
step C consumes artifact B -> final output
```

适合：

- 任务可拆成稳定步骤。
- 每一步有明确输入输出。
- 上一步产物可以结构化传给下一步。

Runtime Core 对应能力：

- `StepRunner`
- `ArtifactRecord`
- `ArtifactStore`
- `ContextBuilder`
- `TraceRecorder`

当前例子：

- `research_mini`
- `code_review_mini`

### Routing

中文理解：路由 / 分流。

结构：

```text
输入
  -> 判断任务类型 / 风险 / 难度
  -> 路由到不同处理链路
```

适合：

- 输入类型差异明显。
- 简单任务和复杂任务应走不同路径。
- 高风险动作需要进入审批或 blocked。

Runtime Core 对应能力：

- `TaskContract`
- `RuntimeState`
- `ToolPolicyChecker`
- `BlockedReason`
- Trace 中的 route decision event

当前边界：

- 当前代码已有工具策略 blocked。
- 尚未实现通用 route decision 记录模型。

### Parallelization

中文理解：并行化。

结构：

```text
任务
  -> 子任务 A
  -> 子任务 B
  -> 子任务 C
  -> 汇总 / 投票 / 交叉检查
```

适合：

- 多个检查可独立进行。
- 需要多个候选答案。
- 需要多角度评估。

Runtime Core 可能需要：

- 多 artifact 分支。
- step group。
- trace branch id。
- 汇总 artifact。

当前边界：

- 当前 `StepRunner` 是线性顺序执行。
- 不应提前实现并行调度，除非后续场景确实需要。

### Orchestrator-Workers

中文理解：编排者-工作者。

结构：

```text
orchestrator 拆解任务
  -> worker 1
  -> worker 2
  -> worker 3
orchestrator 汇总结果
```

适合：

- 任务复杂，需要拆成多个不同子任务。
- 子任务之间职责清楚。
- 每个 worker 可以有不同工具权限。

Runtime Core 可能需要：

- worker task contract。
- handoff artifact。
- worker scoped context。
- unified trace。
- per-worker tool policy。

当前边界：

- 当前 Runtime Core 没有多 worker 调度。
- 如果后续支持，应优先从 artifact handoff 和 trace scope 开始，而不是先做多 Agent 聊天框架。

### Evaluator-Optimizer

中文理解：评估者-优化者。

结构：

```text
generator 生成结果
  -> evaluator 评估结果
  -> optimizer 修正结果
  -> 达标 / 重试 / blocked
```

适合：

- 输出质量难以一次保证。
- 有明确评估标准。
- 可接受额外成本和延迟。

Runtime Core 可能需要：

- evaluation artifact。
- retry budget。
- failure reason。
- blocked reason。
- trace 中记录每次评估和修正。

当前边界：

- 当前 code_review_mini 有 review 和 patch suggestion，但还没有 evaluator-optimizer 闭环。

### Autonomous Agent

中文理解：通用自主 Agent / 开放循环 Agent。

结构：

```text
goal
  -> plan
  -> act
  -> observe
  -> revise
  -> act
  -> stop / blocked
```

适合：

- 路径开放。
- 环境反馈关键。
- 需要多轮诊断、探索或修复。
- 不能提前写死完整流程。

Runtime Core 必须具备：

- 强状态模型。
- 工具权限。
- 上下文治理。
- checkpoint / resume。
- trace / replay。
- retry / budget。
- blocked / human-in-the-loop。

当前判断：

- 当前项目不应直接追求通用自主 Agent。
- 应先通过 workflow 和 agentic workflow 小步验证公共能力。

## 选择策略

### 第一层：先判断路径稳定性

| 判断问题 | 倾向 |
|----------|------|
| 步骤是否稳定且可预先定义？ | Workflow |
| 每一步输入输出是否清晰？ | Workflow |
| 是否只需要模型完成局部判断或生成？ | Workflow + LLM step |
| 下一步是否必须依赖工具返回动态决定？ | Agentic Workflow / Agent |
| 任务路径是否难以穷举？ | Agent |

### 第二层：再判断风险和控制要求

| 判断问题 | 倾向 |
|----------|------|
| 是否会写文件、执行命令、调用外部系统？ | Workflow + Tool Policy |
| 是否涉及高风险动作？ | Workflow + Guardrails + Human Review |
| 是否允许模型自主选择工具？ | Agentic Workflow / Agent |
| 是否必须支持中断恢复？ | Runtime Core checkpoint |
| 是否需要失败后人工处理？ | blocked 终态 |

### 第三层：选择具体模式

| 任务特征 | 推荐模式 |
|----------|----------|
| 多步顺序加工 | Prompt Chaining |
| 按类型、风险或难度分流 | Routing |
| 多候选、多检查器、多角度判断 | Parallelization |
| 上层拆解任务，下层执行子任务 | Orchestrator-Workers |
| 生成后需要评估和修正 | Evaluator-Optimizer |
| 开放路径、多轮环境反馈 | Autonomous Agent |

### 第四层：决定 Runtime Core 介入深度

| 场景复杂度 | Runtime Core 介入方式 |
|------------|----------------------|
| 很小的脚本 | 可以只用简单函数和日志，不必引入 Runtime Core |
| 稳定 workflow | 使用 artifact、trace、context、state 做公共支撑 |
| agentic workflow | 增加 tool policy、checkpoint、blocked、evaluation artifact |
| 自主 agent | 需要完整 state、context、memory、artifact、trace、budget、human-in-the-loop |

## Runtime Core 的角色

Runtime Core 不负责替业务场景决定“怎么完成任务”。它负责提供不同模式都可能复用的公共支撑。

更准确的定位是：

```text
Runtime Core 是 workflow / agentic workflow / agent 的运行支撑层，
不是一个自动把所有任务变成自主 Agent 的框架。
```

| Runtime 能力 | 支撑的模式 | 作用 |
|--------------|------------|------|
| `TaskContract` | 所有模式 | 明确任务目标、输入、成功标准和输出约束 |
| `RuntimeState` | 所有模式 | 记录 step 状态、终态、失败和 blocked |
| `ContextBuilder` | LLM step / Agent | 为当前 step 构造必要工作视图 |
| `MemoryStore` | Agentic Workflow / Agent | 提供跨任务经验和偏好 |
| `ArtifactRecord` | Prompt Chaining / Handoff | 支持结构化产物交接 |
| `TraceRecorder` | 所有模式 | 记录足以复盘的执行过程 |
| `FileCheckpointStore` | 长任务 | 支持中断恢复 |
| `ToolPolicyChecker` | 工具型任务 | 控制工具权限和高风险动作 |

这意味着 Runtime Core 的演进应由模式需求驱动：

- 如果多个场景都需要 prompt chaining，就强化 artifact handoff。
- 如果多个场景都需要 routing，就补 route decision trace。
- 如果多个场景都需要 evaluator-optimizer，就补 evaluation artifact 和 retry budget。
- 如果多个场景都需要并行执行，再考虑 step group 或 DAG。

不要反过来因为 Runtime Core 能做某些抽象，就强迫场景使用复杂模式。

## 当前场景回看

### research_mini

`research_mini` 更接近 prompt chaining workflow：

```text
plan_research
collect_evidence -> EvidenceTable
write_report -> DraftReport
review_report -> ReviewResult
```

它的价值不在于自主性，而在于验证：

- step 串联。
- context 构造。
- artifact 交接。
- checkpoint / resume。
- trace / replay。
- blocked 语义。

因此，`research_mini` 是验证 Runtime Core 基础能力的合适场景，但不应该被解释成完整自主 Agent。

### code_review_mini

`code_review_mini` 也是 workflow，但包含局部 LLM step：

```text
collect_code_context -> CodeSnapshot
llm_or_rule_review  -> ReviewReport
propose_patch       -> PatchSuggestion
```

它体现了 agentic workflow 的雏形：

- LLM 可参与 review。
- ReviewReport 通过 schema artifact 约束。
- PatchSuggestion 不直接写文件。
- 高风险 patch writer 可触发 blocked。
- Trace 记录 reviewer provider、latency、prompt chars 和 response chars。

这个场景说明：很多实际 Agent 产品可以先从 workflow + LLM step + Runtime Core 支撑开始，而不是一开始做全自主代码 Agent。

### D-lite 的启发

D-lite 更接近有限边界内的自愈 Agent：

```text
执行 -> 失败分类 -> 修复尝试 -> 验证 -> 成功 / blocked
```

它比 code_review_mini 更动态，但仍然不是无边界自主 Agent。它的合理形态应是：

- 明确任务集合。
- 明确修复规则和工具权限。
- 明确 retry budget。
- 失败进入 blocked。
- trace 足以复盘。

这也说明，自主性应被限制在经过定义的边界内。

## 后续场景设计检查表

每个新场景开始前，应先填写下面的检查表。

| 问题 | 说明 |
|------|------|
| 任务目标是什么？ | 是否能用一句话定义成功结果。 |
| 输入是什么？ | 用户输入、文件、代码、外部资源还是工具结果。 |
| 输出是什么？ | 文本、结构化 artifact、补丁建议、操作结果还是报告。 |
| 步骤是否稳定？ | 如果稳定，优先 workflow。 |
| 哪些 step 需要 LLM？ | 只把需要判断、生成、总结的部分交给模型。 |
| 下一步是否依赖环境反馈？ | 如果是，考虑 agentic workflow。 |
| 是否有高风险工具？ | 需要 tool policy、审批或 blocked。 |
| 是否需要中断恢复？ | 需要 checkpoint / resume。 |
| 是否需要跨任务经验？ | 需要 memory，但必须有写入门控。 |
| step 之间如何交接？ | 优先 schema artifact，而不是自由文本。 |
| 如何复盘失败？ | 需要 trace 记录 step、tool、artifact、error 和 blocked reason。 |
| 成本和延迟是否可接受？ | 决定是否使用多轮评估、并行或真实 LLM。 |

检查表填写后，再选择模式：

```text
稳定顺序步骤 -> Prompt Chaining
需要分流 -> Routing
需要多候选 -> Parallelization
需要任务拆解 -> Orchestrator-Workers
需要反复改进 -> Evaluator-Optimizer
需要开放行动 -> Autonomous Agent
```

## 经验教训

1. Agent 不是越自主越好。

   越自主，对状态、权限、trace、停止条件和人工介入要求越高。

2. Workflow 不是低级方案。

   对生产系统来说，workflow 常常是更可靠的默认选择。许多有效的 Agentic System 本质上是 workflow + 局部 LLM 判断。

3. Runtime Core 不应扩大任务边界。

   Runtime Core 的职责是支撑任务，不是让任务变复杂。如果引入 Runtime Core 后业务逻辑更难理解，就说明抽象层次可能过早或过重。

4. 模式选择应先于代码实现。

   先判断 workflow / agent，再决定 Runtime 能力。否则很容易把评估、trace、memory、tool policy 变成孤立功能堆叠。

5. 场景驱动比框架驱动更稳。

   只有多个具体场景反复暴露同一类问题，才说明某个能力值得进入 Runtime Core。

## 当前边界

本文只提出选择策略，不实现新代码。

当前暂不做：

- 通用 workflow DSL。
- DAG 调度器。
- 多 Agent 调度框架。
- 自动模式选择器。
- 通用 evaluator-optimizer runtime。
- 通用 autonomous agent loop。

后续如果出现多个场景都需要相同模式，再考虑把对应能力从场景代码中沉淀到 Runtime Core。
