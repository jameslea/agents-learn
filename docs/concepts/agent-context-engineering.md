# Agent 上下文工程：从 Prompt 拼接到可治理的工作视图

> 更新时间：2026-05-19
>
> 本文专题讨论 Agent 系统中的上下文设计。它补充 `agent-core-structure.md` 中 Context / State / Memory 的概念区分，也为 `practice-projects/06-agent-runtime-core` 的 Context Builder 实践提供理论背景。核心判断是：上下文不是“把历史都塞进 prompt”，而是 Runtime 为当前 step 构造出的、可解释、可压缩、可隔离、可评估的工作视图。

## 目录

- [一、为什么需要上下文工程](#一为什么需要上下文工程)
- [二、Context 的基本定义](#二context-的基本定义)
- [三、上下文的类型分层](#三上下文的类型分层)
- [四、上下文生命周期：Write / Select / Compress / Isolate / Evaluate](#四上下文生命周期write--select--compress--isolate--evaluate)
- [五、Context Builder 的职责](#五context-builder-的职责)
- [六、上下文可以包含哪些内容](#六上下文可以包含哪些内容)
- [七、常见问题与治理方式](#七常见问题与治理方式)
- [八、上下文、状态、记忆、产物和 Trace 的边界](#八上下文状态记忆产物和-trace-的边界)
- [九、多 Agent 与工具环境中的上下文隔离](#九多-agent-与工具环境中的上下文隔离)
- [十、当前 06 项目的实现对照](#十当前-06-项目的实现对照)
- [十一、最应该补充实现的部分](#十一最应该补充实现的部分)
- [十二、阶段性结论](#十二阶段性结论)
- [参考资料](#参考资料)

## 一、为什么需要上下文工程

早期 LLM 应用常把问题理解为 prompt engineering：怎样写一段更好的系统提示词，怎样组织 few-shot 示例，怎样描述输出格式。到了 Agent 阶段，这已经不够了。

Agent 会在多轮循环中调用工具、读取文件、检索资料、生成 artifact、接收人工反馈，并在较长时间内推进任务。每一步都会产生新的信息，但模型每次只能看到有限上下文窗口。于是问题从“怎么写 prompt”变成：

```text
在当前 step，哪些信息应该进入模型上下文？
哪些信息应该保存在 state、memory、artifact 或 trace 中？
哪些信息应该被压缩、延迟加载、隔离或排除？
```

Anthropic 将 context engineering 描述为 prompt engineering 的自然演进：它关注的不只是系统提示词，而是推理时进入有限上下文窗口的全部信息，包括系统指令、工具、MCP、外部数据和消息历史。更重要的是，长上下文并不自动等于好上下文。上下文越长，模型越可能出现注意力分散、关键证据被淹没、旧错误继续影响后续步骤等问题。

因此，一个实用判断是：

```text
上下文是有限注意力资源。
目标不是放入最多信息，而是放入当前 step 最需要、最高信号、最低污染的信息。
```

这也是 Agent Runtime 需要 Context Builder 的原因。

## 二、Context 的基本定义

在 Agent 系统中，Context 可以有两个层次的含义。

第一层是模型可见上下文：

```text
模型本次推理时实际看到的 token 集合。
```

第二层是运行时上下文：

```text
Runtime、工具、hook、状态机和编排逻辑可访问的运行时信息。
```

这两个层次必须区分。OpenAI Agents SDK 明确把 context 分为两类：

- Local context：代码、工具、hook 可访问的依赖、状态和运行数据，不会发送给 LLM。
- Agent / LLM context：模型生成回复时真正能看到的信息。

这个区分非常关键。很多 Agent 问题来自把所有信息都当作“模型应该看到的文本”。实际更合理的做法是：

```text
Runtime 能知道很多，
模型只应该看到当前决策必要的一小部分。
```

## 三、上下文的类型分层

一个更完整的上下文系统至少应区分下面几类信息。

| 类型 | 是否给模型看 | 生命周期 | 典型内容 | 主要风险 |
|------|--------------|----------|----------|----------|
| System / Developer Context | 是 | 稳定或版本化 | 角色、边界、输出格式、安全策略 | 写得过长、规则冲突 |
| Step Context | 是 | 当前 step | 当前目标、当前动作、当前 artifact schema | 缺少停止条件或成功标准 |
| Conversation / Session Context | 部分可见 | 当前会话 | 用户近期输入、模型近期输出 | 历史膨胀、旧错误污染 |
| Runtime Local Context | 否 | 当前 run | 依赖对象、logger、审批状态、usage | 误把敏感信息发给模型 |
| State | 通常不直接全文可见 | 当前任务 | step 状态、预算、恢复点、失败原因 | 状态和上下文混用 |
| Memory | 按需可见 | 跨任务 | 用户偏好、项目约定、经验、技能 | 过期、不可信、触发错误 |
| Artifact | 摘要或引用可见 | 任务内或跨任务 | Evidence Table、Draft、ReviewResult | 全文过长、schema 不稳定 |
| Trace | 摘要可见 | 运行记录 | 工具调用、错误、重试、人工介入 | 泄露敏感信息、噪音过大 |
| External Resource | 按需可见 | 外部系统 | 文件、数据库、网页、MCP resources | prompt injection、来源不可信 |
| Tool Descriptions | 是 | 工具版本 | 工具能力、参数、风险、返回结构 | 工具太多、描述重叠 |

这张表的核心含义是：**不是所有信息都应该进入 LLM context**。Agent Runtime 应该先保存、分类、标注，再由 Context Builder 选择当前 step 真正需要的部分。

## 四、上下文生命周期：Write / Select / Compress / Isolate / Evaluate

主流上下文工程越来越倾向于把上下文管理看成一个生命周期，而不是一次性 prompt 拼接。

### 4.1 Write：写入上下文相关信息

Write 不是写入 prompt，而是决定信息应该保存到哪里：

- 当前任务进度写入 `RuntimeState`。
- 中间结果写入 `Artifact`。
- 工具调用和错误写入 `Trace`。
- 跨任务经验写入 `Memory`。
- 大文件或外部资料保留为 `Resource` 引用。

如果没有 Write 层，所有信息只能堆进聊天历史，最终会导致上下文膨胀和无法恢复。

### 4.2 Select：选择当前 step 所需信息

Select 是 Context Builder 的核心动作。它要根据当前 step 的目标、工具、产物 schema、memory tag、artifact 类型和预算选择信息。

选择规则可以从简单确定性规则开始：

- 当前目标始终进入。
- 当前 step 始终进入。
- 最近 step 只进入摘要。
- artifact 按 tag / type / schema 选择。
- memory 按 scope / tag / confidence / freshness 选择。
- trace 默认只进入摘要。

后续可以扩展为检索、ranking、LLM rerank 或手工规则混合。

### 4.3 Compress：压缩上下文

Compress 不是简单截断。更好的压缩方式包括：

- 历史 step 摘要。
- 工具结果摘要。
- artifact 引用替代全文。
- evidence table 替代长段落证据。
- session history compaction。
- 按任务阶段生成 phase summary。

OpenAI Agents SDK 的 session compaction 思路也体现了这一点：当会话历史过长时，用压缩后的等价 conversation items 替代原始长历史。

### 4.4 Isolate：隔离上下文

Isolate 是复杂 Agent 中经常被低估的能力。

隔离可以发生在多个层面：

- 不同 step 看到不同上下文。
- 不同工具只拿到必要参数。
- 不同 Agent 只看到自己职责范围内的信息。
- 外部网页和用户输入不直接污染系统指令。
- sandbox 中的工具输出先进入 state / artifact，再经筛选进入模型。

LangGraph 强调通过 state schema 和 node 级逻辑控制每一步看到的信息，这本质上就是上下文隔离。

### 4.5 Evaluate：评估上下文是否有效

上下文工程不能只凭感觉。应该记录和评估：

- 进入上下文的信息类型占比。
- token / char 预算。
- 被排除信息及原因。
- 是否缺失关键证据。
- 是否引入过期 memory。
- 压缩前后结果是否退化。
- 上下文变更是否改善任务成功率。

这也是 `selection_log` 的价值：它让上下文选择变成可观察对象，而不是隐藏在 prompt 拼接代码里。

## 五、Context Builder 的职责

Context Builder 可以理解为 Runtime Core 中的一个专门组件。它的职责不是调用模型，而是构造模型调用前的工作视图。

一个成熟的 Context Builder 至少包含：

| 子能力 | 作用 |
|--------|------|
| Candidate Collector | 收集可能相关的 state、memory、artifact、trace、resource、tool 描述 |
| Relevance Filter | 根据当前 step、tag、schema、任务目标筛选相关信息 |
| Trust Filter | 根据来源、验证状态、风险等级、是否外部输入判断可信度 |
| Freshness Filter | 判断 memory、artifact、tool result 是否过期 |
| Compressor | 对历史、工具结果、artifact 和 trace 做摘要或引用化 |
| Budget Manager | 控制 token / char 预算，决定优先级 |
| Prompt Assembler | 按稳定结构组装 LLM-visible context |
| Selection Logger | 记录每条信息进入或排除的原因 |
| Safety Filter | 防止敏感信息、凭证、注入内容进入模型上下文 |

当前 06 项目只实现了其中一小部分，但方向是正确的：先做确定性筛选和 selection log，再逐步增强。

## 六、上下文可以包含哪些内容

上下文不是固定模板，而是按 step 构造。常见内容包括：

| 内容 | 是否应直接进入模型 | 说明 |
|------|--------------------|------|
| 系统指令 | 是 | 稳定边界、角色、输出规则、安全限制 |
| 当前任务目标 | 是 | 模型必须知道要完成什么 |
| 当前 step | 是 | 当前轮次的直接工作目标 |
| 成功标准 | 是 | 判断何时完成或失败 |
| 输出 schema | 是 | 约束结构化输出 |
| 最近 step 摘要 | 部分进入 | 只保留必要摘要 |
| 上一步观察结果 | 部分进入 | 工具返回过长时先摘要 |
| artifact 摘要 / 引用 | 部分进入 | 优先引用稳定 artifact |
| evidence table | 常进入 | 比长篇证据更可控 |
| memory | 按需进入 | 需要 scope、tag、confidence、freshness |
| tool descriptions | 按需进入 | 工具过多时应做选择和分组 |
| external resources | 按需进入 | 需要来源和信任等级 |
| trace | 通常不直接进入 | 默认只进入 trace summary |
| credentials / secrets | 不应进入 | 只能留在 local context 或 secret store |
| 原始完整历史 | 通常不应进入 | 应通过 session、summary、artifact 管理 |

## 七、常见问题与治理方式

| 问题 | 表现 | 治理方式 |
|------|------|----------|
| 上下文膨胀 | 历史、工具结果、文档全部塞入 prompt | 摘要、artifact 引用、预算管理、session compaction |
| 上下文污染 | 旧错误、无关讨论、低质量输出进入当前决策 | selection log、memory 验证、版本和有效期 |
| 关键证据缺失 | 模型没有看到必要来源或约束 | evidence table、required context check、schema validation |
| 工具描述过载 | 工具太多，模型选错或不用 | 工具分组、tool retrieval、最小可用工具集 |
| 记忆误触发 | 不相关偏好或旧经验影响当前任务 | scope、tag、confidence、freshness、human validation |
| 多 Agent 交接不清 | 下游只读上游自由文本 | schema artifact、handoff contract、独立 evaluation |
| prompt injection | 外部网页或文件诱导越权行为 | trust level、source boundary、安全过滤、工具权限 |
| 敏感信息泄露 | key、token、路径或隐私内容进入 prompt / trace | sensitive 标记、redaction、local-only context |
| 预算失控 | token、模型调用和工具调用膨胀 | budget manager、max steps、trace usage |
| 压缩导致信息丢失 | 摘要漏掉关键事实 | 压缩评估、引用原始 artifact、人工复核 |

## 八、上下文、状态、记忆、产物和 Trace 的边界

上下文工程最容易出错的地方，是把所有信息都塞进 prompt。更合理的分工是：

| 结构 | 保存什么 | 是否直接给模型 | 作用 |
|------|----------|----------------|------|
| Context | 当前 step 必要信息 | 是 | 支撑当前推理 |
| State | 当前任务进度和恢复点 | 通常摘要进入 | 支撑执行、恢复、复盘 |
| Memory | 跨任务经验和偏好 | 按需进入 | 支撑长期复用 |
| Artifact | 结构化中间产物 | 摘要或引用进入 | 支撑交接、验证、复用 |
| Trace | 执行过程记录 | 通常摘要进入 | 支撑复盘、审计、评估 |
| Local Context | 工具和 Runtime 可访问依赖 | 否 | 支撑运行时代码和工具调用 |

一个重要原则是：

```text
凡是后续必须依赖、失败后必须复盘、恢复时必须重建的信息，
不应该只存在于 LLM context 中。
```

它应该进入 state、artifact、memory 或 trace。

## 九、多 Agent 与工具环境中的上下文隔离

多 Agent 不应该共享一个大上下文。合理的多 Agent 应该隔离：

- 职责。
- 工具权限。
- 输入信息。
- 输出 artifact。
- 评估标准。

例如研究 Agent 可以看到搜索结果和 evidence table，写作 Agent 可以看到 evidence table 和写作约束，审阅 Agent 可以看到 draft report 和 rubric，但不一定需要看到完整搜索 trace。

工具环境也需要上下文隔离：

- 工具只接收必要参数。
- 工具结果先进入 artifact 或 state。
- 高风险工具需要 policy 和审批。
- 外部资源带来源、信任等级和敏感性标记。

MCP 的 resources、tools、prompts、roots 等概念也说明，现代 Agent 的上下文不只是文本 prompt，而是由外部资源、工具能力和访问边界共同组成的运行环境。

## 十、当前 06 项目的实现对照

当前 `practice-projects/06-agent-runtime-core` 的阶段 1 已实现一个最小 Context Builder。

| 能力 | 当前实现 |
|------|----------|
| 任务目标 | `TaskContract.goal` 始终进入 |
| 当前 step | `current_step` 始终进入 |
| 最近 step 摘要 | 从 `RuntimeState.steps` 取最近 N 条 |
| 策略控制 | `ContextPolicy` 管理预算、trace 摘要、敏感候选、不可信候选和 required context |
| 统一候选 | `ContextCandidate` 统一承载 artifact、memory、trace、resource 等候选 |
| artifact 候选 | `ArtifactCandidate` 按 tag 选择，只放摘要和路径 |
| memory 候选 | `MemoryCandidate` 按 scope、tag、confidence、validated、expires_at 筛选 |
| 可见性 | `ContextVisibility` 区分 `llm_visible`、`summary_only`、`runtime_only` |
| 信任等级 | `ContextTrustLevel` 标记 system、tool、artifact、memory、external、untrusted |
| 敏感拦截 | `sensitive=True` 的候选默认不进入模型上下文 |
| trace | 只放 `trace_summary`，不放原始 trace |
| 预算 | `max_item_chars` 和 `max_context_chars` |
| 可解释性 | `ContextSelection` 记录 included / excluded 和 reason |
| 指标 | `ContextMetrics` 记录 item 数、排除数、类型分布、预算占比和 required context 缺失数 |
| required context | 缺少必要 source 或 artifact type 时将 bundle 标记为 not ready |

这个实现目前覆盖了：

- Select：按 tag、scope、confidence、freshness 选择。
- Compress：摘要和字符预算。
- Isolate：不直接塞完整 trace / artifact，且支持 runtime-only 候选。
- Evaluate：使用 selection log 和 ContextMetrics 做初步可观测。

## 十一、最应该补充实现的部分

后续最值得优先补充的不是复杂向量检索，而是在现有元数据、策略和指标基础上继续补齐安全、压缩质量和复盘能力。

### 11.1 补齐治理元数据

当前已具备 `visibility`、`trust_level`、`sensitive`、`expires_at`、`confidence` 等基础字段。后续更值得补充：

| 字段 | 作用 |
|------|------|
| `source_uri` | 记录来源路径、URL、artifact id 或 tool call id |
| `provenance` | 说明信息如何产生 |
| `token_estimate` | 支撑预算管理 |
| `priority` | 支撑预算不足时的裁剪 |

### 11.2 增强 ContextCandidate 来源适配

当前已经有 `ContextCandidate`，但 state、artifact、memory、trace、resource、tool description 还没有统一适配层。后续应补：

```text
State -> ContextCandidate
Artifact -> ContextCandidate
MemoryRecord -> ContextCandidate
TraceSummary -> ContextCandidate
ToolSpec -> ContextCandidate
```

这样可以避免每种来源都在 `ContextBuilder` 里写专用逻辑。

### 11.3 增强 ContextPolicy

当前 `ContextPolicy` 已支持基础预算、trace、敏感候选、不可信候选和 required context。后续可加入：

```text
allowed_source_types
source_type_budget
priority_rules
required_tags
tool_description_limit
```

这会让不同 Agent / step 可以使用不同上下文策略。

### 11.4 增加安全过滤和脱敏

至少要实现：

- API key / token / password 正则脱敏。
- 外部资源默认 `untrusted`。
- untrusted 内容不能覆盖系统指令。
- tool output 进入模型前先经过摘要或安全过滤。

### 11.5 增强上下文指标

当前已有基础 `ContextMetrics`。后续可以补：

```text
token_estimate
compression_ratio
required_context_coverage
trust_level_breakdown
visibility_breakdown
```

这些指标后续可以进入 trace，用于复盘和评估。

### 11.6 增强 required context 检查

某些 step 必须依赖特定 artifact 或 schema。例如写报告必须有 `EvidenceTable`，审阅必须有 `DraftReport`。

当前已支持 `required_source_ids` 和 `required_artifact_types`。后续可以增加：

```text
required_tags
required_schema_version
required_confidence
```

缺少必要上下文时，不应该让模型硬写，而应该进入 `blocked` 或 `failed`。

### 11.7 增加上下文版本和 diff

在长任务中，应能比较两次 step 的上下文差异：

- 新增了哪些信息。
- 删除了哪些信息。
- 哪些 memory 被替换。
- 哪些 artifact 版本变化。

这对复盘“为什么这次输出变差”很重要。

## 十二、阶段性结论

上下文工程是 Agent Runtime 的核心能力之一。它不是 prompt 技巧，而是连接 state、memory、artifact、trace、tool 和模型调用的运行时机制。

一个成熟 Agent 不应该让模型在无限增长的聊天历史里自行找重点，而应该由 Runtime 明确管理：

```text
保存在哪里，
什么时候选择，
如何压缩，
如何隔离，
如何评估，
如何解释。
```

当前项目的正确推进方向，是先把 Context Builder 做成可解释、可观测、可测试的小核心，再逐步引入 memory、artifact、checkpoint、trace 和最小 runtime 串联。

## 参考资料

- [Anthropic：Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic：Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI Agents SDK：Context Management](https://openai.github.io/openai-agents-js/guides/context/)
- [OpenAI Agents SDK：Sessions](https://openai.github.io/openai-agents-js/guides/sessions/)
- [LangChain：Context engineering for agents](https://www.langchain.com/blog/context-engineering-for-agents)
- [Model Context Protocol：Server concepts](https://modelcontextprotocol.io/docs/learn/server-concepts)
