# Agent 系统非功能能力总览

## 目录

- [一、为什么要单独讨论非功能能力](#一为什么要单独讨论非功能能力)
- [二、五个核心问题](#二五个核心问题)
- [三、上下文如何构造](#三上下文如何构造)
- [四、记忆如何保存](#四记忆如何保存)
- [五、状态如何恢复](#五状态如何恢复)
- [六、产物如何交接](#六产物如何交接)
- [七、过程如何复盘](#七过程如何复盘)
- [八、五类能力如何协同](#八五类能力如何协同)
- [九、不同项目规模下如何取舍](#九不同项目规模下如何取舍)
- [十、如何从业务代码中识别非功能模块](#十如何从业务代码中识别非功能模块)
- [十一、成熟度分层](#十一成熟度分层)
- [十二、常见反模式](#十二常见反模式)
- [十三、当前 Runtime Core 的意义和边界](#十三当前-runtime-core-的意义和边界)
- [十四、后续实践原则](#十四后续实践原则)

## 一、为什么要单独讨论非功能能力

Agent 项目最容易被看到的是业务能力：调研、写作、代码审查、运维自愈、客服问答、数据分析、工具调用。但真正决定 Agent 能否从 demo 走向可靠系统的，往往不是这些业务能力本身，而是围绕它们的一组非功能性能力。

这些能力包括：

```text
上下文如何构造
记忆如何保存
状态如何恢复
产物如何交接
过程如何复盘
```

它们不是某一个场景独有的业务逻辑，而是大多数 Agent 系统都会遇到的运行时问题。

如果没有这些能力，Agent 仍然可以跑起来，但会出现几个典型问题：

- 模型输出看似合理，但不知道它到底看到了哪些上下文。
- 任务失败后只能重跑，无法从中断点继续。
- 多个 step 之间靠自由文本交接，字段缺失和格式漂移很难控制。
- 长期记忆和当前任务状态混在一起，错误经验会被反复带入后续任务。
- 失败后只能猜测是 prompt、模型、工具、输入还是中间产物出了问题。

因此，生产级 Agent 的难点不是“让 LLM 调一次工具”，而是：

```text
把不确定的模型调用放进一个可控、可恢复、可交接、可复盘的软件边界里。
```

当前 `practice-projects/06-agent-runtime-core` 的价值，就在于把这些能力从具体业务场景中识别出来，并用最小代码验证它们是否可以作为 Runtime Core 的公共支撑。

## 二、五个核心问题

这五个问题不是并列堆放的清单，而是围绕一次 Agent 任务运行逐步展开的。可以先把一次多 step Agent 任务想象成下面的过程：

```text
接收任务
  -> 为当前 step 选择上下文
  -> 执行模型或工具
  -> 生成中间产物
  -> 更新状态并保存恢复点
  -> 记录过程以便复盘
  -> 进入下一个 step
```

在这个过程中，系统会反复遇到五个非功能问题。它们分别对应“看什么、记什么、怎么继续、怎么交接、怎么复盘”：

| 问题 | 非功能能力 | 对应阶段文档 |
|------|------------|--------------|
| 当前 step 应该看到什么 | Context Builder / 上下文治理 | [01-context-builder.md](01-context-builder.md) |
| 什么应该被保存为经验 | Memory / State 分层 | [02-memory-state.md](02-memory-state.md) |
| 任务中断后如何继续 | Checkpoint / Resume | [03-checkpoint-resume.md](03-checkpoint-resume.md) |
| step 之间如何可靠交接 | Schema Artifact | [04-schema-artifact.md](04-schema-artifact.md) |
| 失败后如何定位原因 | Trace / Replay | [05-trace-replay.md](05-trace-replay.md) |

这张表回答的是“有哪些问题”。但这些问题在运行时不是孤立发生的，而是通过一组 Runtime 对象串成执行链路：

```text
TaskContract
  -> ContextBundle
  -> Step Execution
  -> ArtifactRecord
  -> RuntimeState / Checkpoint
  -> TraceEvent
  -> 下一轮 ContextBundle
```

这条链路可以这样理解：

| 对象 | 在链路中的作用 | 回答的问题 |
|------|----------------|------------|
| `TaskContract` | 定义任务目标、输入和成功标准 | 这次任务要做什么 |
| `ContextBundle` | 为当前 step 装配必要信息 | 当前 step 应该看到什么 |
| `MemoryRecord` | 提供经过筛选的跨任务经验 | 哪些经验可以复用 |
| `ArtifactRecord` | 保存 step 产出的结构化中间结果 | 下游 step 如何接收上游结果 |
| `RuntimeState` | 记录当前进度、step 状态和 artifact 引用 | 执行到哪里，如何恢复 |
| `Checkpoint` | 保存可恢复状态快照 | 中断后如何继续 |
| `TraceEvent` | 记录关键执行事件 | 失败后如何复盘 |

因此，五个核心问题可以从两个层面理解：

- 从概念层看，它们是 Agent 系统绕不开的非功能问题。
- 从实现层看，它们分别落到 context、memory、state、artifact、checkpoint 和 trace 这些 Runtime 对象上。

后面的章节会按这五个问题逐一展开。

## 三、上下文如何构造

上下文治理回答的问题是：

```text
当前 step 需要哪些信息？
哪些信息不应该进入模型？
如何避免上下文膨胀、污染和遗漏？
```

传统 LLM 应用容易把上下文理解成“聊天历史”或“把所有资料拼进 prompt”。这在简单问答中可能能用，但在 Agent 系统中会迅速失控。Agent 的上下文可能来自任务目标、用户输入、历史 step、工具结果、artifact、memory、trace、外部文档和运行时策略。它们的来源、可信度、可见性和生命周期都不同。

因此，Context Builder 的核心职责不是拼字符串，而是构造当前 step 的工作视图。

一个合理的 Context Builder 至少要考虑：

| 维度 | 说明 |
|------|------|
| 来源 | goal、current step、step summary、artifact、memory、trace summary、external input |
| 可见性 | 是否允许进入 LLM，可否只进入摘要，是否仅 Runtime 内部使用 |
| 信任等级 | system、tool、artifact、memory、external、untrusted |
| 相关性 | 是否和当前 step 的目标、tag、artifact type 匹配 |
| 预算 | 字符、token、成本和延迟预算 |
| 安全 | 敏感信息、不可信外部内容、prompt injection 风险 |
| 可解释性 | 为什么进入上下文，为什么被排除 |

当前项目中的 `ContextBuilder` 已经验证了这些最小机制：

- 任务目标和当前 step 总是进入上下文。
- 最近 step 只以摘要形式进入。
- artifact 默认进入摘要、路径和 schema，不读取完整 payload。
- memory 需要经过 scope、tag、confidence、validated、expires_at 等条件筛选。
- 不可信外部候选、敏感候选和 runtime-only 候选默认被拦截。
- `selection_log` 记录每条候选为什么进入或被排除。
- `ContextMetrics` 记录上下文数量、预算使用和排除数量。

这说明上下文治理不是 prompt 工程的小技巧，而是 Agent Runtime 的基础能力。

生产环境中，上下文治理还会继续扩展：

- token 级预算，而不是字符级估算。
- LLM 或 embedding 辅助摘要和检索。
- prompt injection 检测。
- 上下文版本和回放。
- 针对不同模型的上下文策略。
- 多 agent 之间的上下文隔离。

但这些都应该建立在最小 Context Builder 机制之上，而不是直接把所有历史塞给模型。

## 四、记忆如何保存

记忆管理回答的问题是：

```text
哪些信息值得跨任务保存？
哪些只是当前任务状态？
哪些应该保存为 artifact？
记忆如何验证、失效和替换？
```

Agent 项目中一个常见混乱点，是把 memory、state、artifact、trace 都称为“记忆”。这会导致系统越来越不可控。

当前项目把它们区分为：

| 类型 | 作用 | 示例 |
|------|------|------|
| Memory | 跨任务可复用经验 | 用户偏好、项目规范、常见问题模式 |
| State | 当前任务执行状态 | 当前 step、已完成 step、artifact id、少量运行时值 |
| Artifact | 当前任务产生的结构化产物 | 证据表、审查报告、补丁建议 |
| Trace | 执行过程记录 | tool call、error、artifact created、human required |

这个区分非常重要。Memory 不是当前任务的临时变量，也不是完整日志，更不是随手把 LLM 输出保存下来。Memory 应该有明确的写入门槛。

当前项目中的 `MemoryWriteGate` 验证了一个基本判断：

```text
记忆写入不能是“模型觉得重要就保存”，而应该经过 gate。
```

记忆写入至少要考虑：

| 条件 | 说明 |
|------|------|
| 复用价值 | 是否可能在后续任务中再次使用 |
| 来源 | 来自用户、工具、artifact、人工确认还是模型推断 |
| 可信度 | 是否经过验证，confidence 是否足够高 |
| 范围 | global、project、task、user、scenario |
| 标签 | 后续如何被检索和选择 |
| 敏感性 | 是否包含凭证、隐私、路径、内部信息 |
| 有效期 | 是否会过期，是否绑定版本 |
| 冲突 | 是否和已有记忆矛盾 |

当前实现仍然是内存版 `MemoryStore`，但已经覆盖了主要机制：

- 写入 proposal。
- gate 决策。
- active / proposed / expired 状态。
- scope 和 tag 检索。
- confidence 排序。
- 失效和替换。
- 将检索结果交给 Context Builder。

这已经足以说明一个结论：

```text
记忆系统不是“保存更多东西”，而是控制什么东西有资格长期影响未来任务。
```

生产级记忆系统还需要：

- 持久化 store。
- 用户、项目、团队隔离。
- 审计日志。
- 冲突检测。
- 语义检索。
- 人工确认或自动验证。
- 记忆效果评估。

但在小型项目中，可以只保留少量人工维护的 project memory，甚至不做自动写入。

## 五、状态如何恢复

可恢复执行回答的问题是：

```text
任务执行到哪里了？
哪些 step 已经完成？
中断后能否继续？
恢复时哪些内容不能重复执行？
```

Agent 任务往往比普通 LLM 调用更长。它可能包含多个模型调用、多个工具调用、多个中间产物和人工介入点。只要任务足够长，就一定会遇到中断、超时、工具失败、网络失败、进程退出或人工暂停。

没有 checkpoint 的 Agent 系统，失败后通常只有两个选择：

- 从头重跑，浪费成本，并可能产生不同结果。
- 人工猜测执行到哪里，再手动补救。

这两种方式都不适合生产环境。

当前项目中的 `RuntimeState` 和 `FileCheckpointStore` 验证了最小恢复语义：

- `RuntimeState` 保存 task id、task type、任务状态、当前 step、step 列表、artifact id 和少量运行时值。
- 每个 step 成功后保存 checkpoint。
- resume 时读取 checkpoint。
- 已经 `PASSED` 的 step 不重复执行。
- 恢复时将跳过的 step 显式记录为 `SKIPPED`。
- 任务可以进入 `interrupted`、`failed`、`blocked`、`completed` 等状态。

这里的关键点是：

```text
checkpoint 保存的是结构化状态，不是完整聊天历史。
```

checkpoint 不应该替代 artifact store，也不应该替代 trace。它只回答“当前任务恢复执行需要的最小状态是什么”。

生产环境中，checkpoint 会进一步复杂化：

| 问题 | 生产级要求 |
|------|------------|
| RUNNING step 中断 | 判断是否重试、回滚、跳过或人工介入 |
| 工具副作用 | 避免重复执行写操作 |
| 并发任务 | checkpoint 需要事务和隔离 |
| 版本升级 | checkpoint schema 需要 version 和迁移 |
| 长期任务 | checkpoint 与 artifact store、trace store 一致性 |
| 人工介入 | checkpoint 要记录 pending action 和审批状态 |

当前项目没有直接实现这些生产级能力，但已经验证了最小模型：

```text
Agent 长任务必须显式记录进度，否则无法可靠恢复。
```

## 六、产物如何交接

结构化产物交接回答的问题是：

```text
上游 step 产出了什么？
下游 step 如何消费？
字段是否稳定？
缺字段、错 schema 或未验证产物如何处理？
```

许多 Agent demo 中，step 之间靠自然语言交接。例如：

```text
Researcher 输出一段文字
Writer 从文字里自己理解证据
Reviewer 再从报告里猜问题
```

这种方式在 demo 中看起来简单，但在复杂任务中很脆弱。自由文本可能格式漂移、字段缺失、含义模糊、顺序变化，甚至包含模型幻觉。下游 step 不得不重新解析、猜测和容错。

Schema Artifact 的核心判断是：

```text
step 之间应该通过结构化产物交接，而不是靠自由文本猜字段。
```

当前项目中的 `ArtifactRecord` 和 `ArtifactStore` 验证了最小交接语义：

- artifact 有 id、type、title、summary、path、schema_name、producer_step_id、tags、payload、validated、metadata。
- `summary` 用于进入 context。
- `payload` 用于结构化消费。
- 保存 artifact 时做 schema 校验。
- 下游消费 artifact 时再次做 schema 校验。
- 未验证或 schema 不匹配的 artifact 不应继续传播。

这解决了几个关键问题：

| 问题 | Artifact 机制的回答 |
|------|---------------------|
| 下游如何知道字段 | 通过 Pydantic schema |
| 如何引用上游产物 | 通过 artifact_id |
| 如何进入上下文 | 只进入 summary / path / schema |
| 如何避免上下文膨胀 | 不把完整 payload 直接塞进 prompt |
| 如何复盘交接链路 | trace 记录 artifact created / consumed |

在 `research_mini` 中，artifact 是：

```text
EvidenceTable -> DraftReport -> ReviewResult
```

在 `code_review_mini` 中，artifact 是：

```text
CodeSnapshot -> ReviewReport -> PatchSuggestion
```

这说明 Schema Artifact 不是某一个业务场景的特例，而是 Agent step 交接的通用模式。

生产级场景还需要：

- 持久化 artifact store。
- artifact version。
- schema migration。
- 大文件和二进制产物管理。
- artifact 权限和隔离。
- artifact 与 trace、checkpoint 的一致性。

但最小原则已经明确：

```text
业务 step 可以是智能的，但 step 之间的交接接口应该尽量是确定的。
```

## 七、过程如何复盘

Trace 与复盘回答的问题是：

```text
任务为什么成功？
任务为什么失败？
是哪一步失败？
失败和哪个输入、工具、artifact、模型输出有关？
是否可以重试，还是需要人工介入？
```

Trace 不是普通日志。普通日志常常是给开发者看的文本流，而 Agent trace 应该是运行时事件链。它要记录任务执行中的关键事件，并支持失败后的结构化复盘。

当前项目中的 `TraceEvent`、`TraceRecorder`、`TraceReader` 和 `TraceReplaySummary` 验证了最小 trace 机制。

Trace 事件包括：

| 事件 | 含义 |
|------|------|
| `task_started` | 任务开始 |
| `task_finished` | 任务结束 |
| `step_started` | step 开始 |
| `step_passed` | step 成功 |
| `step_failed` | step 失败 |
| `artifact_created` | 产物创建 |
| `artifact_consumed` | 产物消费 |
| `tool_called` | 工具调用或策略检查 |
| `human_required` | 需要人工介入 |

Trace 的价值在于让失败不再只是一个最终错误，而是一条可阅读的执行链：

```text
task_started
step_started
tool_called
artifact_created
step_passed
...
step_failed / human_required
```

当前项目还验证了几个重要边界：

- trace 记录关键事件和摘要，不记录完整上下文。
- artifact 进入 trace 时记录 id、schema、path，不记录完整 payload。
- tool call 记录工具名、参数摘要、风险等级。
- 写入前做基础敏感字段脱敏。
- replay summary 汇总失败 step、artifact 流转、风险事件和人工介入事件。

这背后的核心原则是：

```text
Trace 要足以复盘，但不能过载，也不能泄露敏感信息。
```

生产级 trace 还需要：

- trace id / run id / span id。
- 外部后端，如 Langfuse、LangSmith、Phoenix。
- token、latency、cost、provider、model 记录。
- tool 参数和输出的分级脱敏。
- 与评估系统和告警系统连接。
- trace 回放和对比。

但即使是小项目，也建议至少保留 JSONL trace 或结构化运行记录。没有 trace，Agent 调试会退化成反复猜 prompt。

## 八、五类能力如何协同

这五类能力不是孤立模块。它们构成一个运行闭环。

一次典型 Agent step 可以这样理解：

```text
1. RuntimeState 告诉系统当前执行到哪个 step。
2. ContextBuilder 根据 task、state、memory、artifact、trace summary 构造 ContextBundle。
3. 模型或规则执行当前 step。
4. 结果保存为 ArtifactRecord。
5. RuntimeState 更新 step 状态和 artifact 引用。
6. TraceRecorder 记录 step、tool、artifact 和错误事件。
7. Checkpoint 保存最新 RuntimeState。
8. 下一个 step 通过 ContextBuilder 和 ArtifactStore 消费上一步结果。
```

这说明每个模块都有明确边界：

| 模块 | 主要职责 | 不应该承担 |
|------|----------|------------|
| Context | 选择当前 step 可见信息 | 保存完整历史、替代 memory |
| Memory | 保存跨任务经验 | 保存当前任务进度 |
| State | 保存当前执行进度 | 保存完整 artifact payload |
| Artifact | 保存结构化产物 | 替代 trace 或自由塞进 context |
| Trace | 记录执行过程 | 替代业务产物或 checkpoint |
| Checkpoint | 支持恢复 | 替代 trace 审计 |

一旦这些边界混乱，系统就会出现连锁问题：

- 把 trace 当 context，会导致上下文噪音过大。
- 把 artifact payload 当 context，会导致上下文膨胀。
- 把 state 当 memory，会把临时错误带入未来任务。
- 把 memory 当事实库，会传播未经验证的信息。
- 把 checkpoint 当 artifact store，会导致恢复时找不到结构化产物。

因此，Runtime Core 的核心价值不是“多几个类”，而是为这些信息建立边界和流转方式。

## 九、不同项目规模下如何取舍

并不是所有 Agent 项目都需要一次性实现完整 Runtime Core。不同项目可以做不同取舍。

| 项目类型 | 合理取舍 |
|----------|----------|
| 一次性 demo | 可以只保留最小 prompt、人工观察和简单日志 |
| 个人探索项目 | 建议保留 context summary、结构化输出和 JSONL trace |
| 小型内部工具 | 建议加入 schema artifact、基础 checkpoint、tool policy |
| 长任务 Agent | checkpoint / resume、artifact store、trace 基本不可少 |
| 高风险工具 Agent | tool policy、blocked、人类审批、trace 必须优先 |
| 多人协作 Agent | 持久化 store、权限隔离、审计、版本治理需要考虑 |
| 生产级 Agent | 这些能力都需要，并且要接入监控、告警、成本治理和回滚机制 |

可以用下面的方式判断是否需要某个能力：

| 问题 | 如果答案是“是” | 应优先补充 |
|------|----------------|------------|
| 任务会运行多步或几分钟以上吗 | 是 | checkpoint / resume |
| 下游依赖上游输出吗 | 是 | schema artifact |
| 输出错误后需要定位原因吗 | 是 | trace / replay |
| 工具有副作用吗 | 是 | tool policy / approval |
| 信息会跨任务复用吗 | 是 | memory gate |
| 上下文来源很多吗 | 是 | context builder |
| 多人会维护或审查系统吗 | 是 | 持久化、审计、版本治理 |

对于探索性项目，过早引入完整 Runtime 会拖慢开发。对于生产级 Agent，缺失这些能力会在后期以更高成本返工。

更现实的策略是：

```text
先保留最小可观察性：
Context summary + Artifact + Trace log

任务变长后：
加入 Checkpoint / Resume

工具有副作用后：
加入 Tool Policy / Approval / Blocked

需要跨任务学习后：
加入 Memory Gate

进入团队和生产后：
加入持久化、权限、审计、监控和版本治理
```

## 十、如何从业务代码中识别非功能模块

场景驱动开发 Runtime Core 的关键，是不断区分：

```text
哪些代码属于业务本身？
哪些代码其实是 Agent 系统的公共支撑？
```

以 `code_review_mini` 为例：

| 内容 | 归属 |
|------|------|
| 判断 `os.system` 有风险 | 业务逻辑 |
| 定义 `CodeFinding` schema | 场景 artifact schema |
| 保存 `ReviewReport` artifact | Runtime Core 机制 |
| 记录 LLM provider、model、latency | Runtime / Observability 机制 |
| 判断 patch writer 需要审批 | Tool policy 机制 |
| 决定是否只输出 patch suggestion | 场景策略 |
| 中断后跳过已完成 step | Runtime Core 机制 |

识别非功能模块可以问这些问题：

| 判断问题 | 如果答案是“是”，可能应抽象 |
|----------|----------------------------|
| 这个逻辑是否会在多个 Agent 场景反复出现 | 是 |
| 它是否和业务领域无关 | 是 |
| 它是否用于可靠性、可恢复、可复盘、安全、治理 | 是 |
| 它是否可以通过稳定接口被场景调用 | 是 |
| 它是否能用测试验证，不依赖某个具体 prompt | 是 |

反过来，如果一个逻辑只服务单个场景，就应该先留在 `scenarios/<name>/` 中，不要急着抽入 Runtime Core。

当前项目采用的原则是：

```text
先让场景使用 Runtime Core，
再根据真实摩擦优化 Runtime Core，
不要凭空设计大框架。
```

## 十一、成熟度分层

这五类能力可以按成熟度分层理解。

### Level 0：脚本级

特征：

- 直接写 prompt。
- 直接调用模型。
- 靠 print 和人工观察。
- 无 checkpoint，无 artifact，无 trace。

适合：

- 一次性 demo。
- 快速验证想法。

风险：

- 失败不可复盘。
- 结果不可稳定复现。

### Level 1：结构化输出

特征：

- 使用 Pydantic / JSON schema 约束输出。
- 保存少量 artifact。
- 有简单日志。

适合：

- 小型内部工具。
- 单人项目。

风险：

- 长任务中断后仍难恢复。
- 记忆和状态可能混乱。

### Level 2：最小 Runtime

特征：

- Context Builder。
- Memory / State / Artifact 分层。
- Checkpoint / Resume。
- JSONL Trace。
- Tool Policy。
- Blocked 终态。

适合：

- 多步 Agent。
- 可恢复任务。
- 工具有一定风险的项目。

当前 `06-agent-runtime-core` 大致处于这个层级。

### Level 3：团队级 Runtime

特征：

- 持久化 memory / artifact / trace store。
- run id、version、schema migration。
- 人工审批流。
- 权限和隔离。
- 更完整的成本、延迟和 provider 观测。

适合：

- 团队协作。
- 长期运行任务。
- 内部生产工具。

### Level 4：生产级 Agent 平台

特征：

- 多租户。
- 审计和权限系统。
- 外部 trace backend。
- 监控、告警、回滚。
- 评估体系。
- 灰度发布和版本治理。
- 安全扫描和 prompt injection 防御。

适合：

- 面向用户或企业的 Agent 产品。
- 高风险工具调用。
- 大规模并发任务。

这个层级不应由当前项目直接追求，但当前项目的五类能力是进入该层级的基础。

## 十二、常见反模式

### 1. 把所有历史都塞进 prompt

问题：

- 上下文膨胀。
- 模型注意力分散。
- 敏感信息泄露。
- 历史错误反复影响当前 step。

应对：

- 使用 Context Builder。
- 区分 summary、artifact、memory、trace。
- 保留 selection log。

### 2. 把 LLM 输出直接当下游输入

问题：

- 字段漂移。
- 缺少校验。
- 下游解析复杂。

应对：

- 使用 schema artifact。
- 保存和消费时都做校验。

### 3. 把当前状态写成长久记忆

问题：

- 临时信息污染未来任务。
- 错误推断被长期复用。

应对：

- 区分 memory 和 state。
- 使用 MemoryWriteGate。

### 4. 没有 checkpoint，失败就重跑

问题：

- 成本高。
- 副作用工具可能重复执行。
- 结果不稳定。

应对：

- step 成功后保存 checkpoint。
- 恢复时跳过已完成 step。
- 对高风险工具增加幂等和审批策略。

### 5. 没有 trace，只看最终输出

问题：

- 无法定位失败原因。
- 无法判断是模型、工具、输入还是中间产物问题。

应对：

- 记录 runtime 关键事件。
- 记录 artifact created / consumed。
- 记录 tool risk、provider、latency、error。

### 6. 过早做通用 Runtime 大框架

问题：

- 抽象脱离场景。
- 增加学习和接入成本。
- 小项目被框架复杂度拖垮。

应对：

- 场景驱动。
- 两个以上场景反复需要的能力再抽回 core。
- 保持小核心。

## 十三、当前 Runtime Core 的意义和边界

当前 `practice-projects/06-agent-runtime-core` 已经验证了五类基础非功能能力：

- `context/`：上下文构造和治理。
- `memory/`：长期记忆和写入 gate。
- `task/`：任务契约和运行状态。
- `artifact/`：结构化产物保存和校验。
- `observability/`：checkpoint 和 trace。
- `execution/`：最小 Runtime 串联和 tool policy。

它通过两个场景做了验证：

| 场景 | 作用 |
|------|------|
| `research_mini` | 验证 research -> evidence -> report -> review 的结构化流程 |
| `code_review_mini` | 验证代码审查、真实 LLM reviewer、patch suggestion 和 tool policy |

当前项目的意义不是已经完成一个生产级 Runtime，而是确认了：

```text
业务逻辑可以留在场景中，
非功能性支撑能力可以逐步隔离出来，
Runtime Core 应该由真实场景反复验证后再演进。
```

当前边界也很明确：

- MemoryStore 仍是内存版。
- ArtifactStore 仍是内存版，靠 snapshot 支撑命令级 resume。
- Trace 仍是本地 JSONL。
- Tool policy 只是最小策略检查。
- 没有 DAG 调度。
- 没有完整成本治理。
- 没有外部 observability backend。

这些不是失败，而是当前阶段的取舍。

## 十四、后续实践原则

后续继续做 Agent 场景时，可以遵循下面原则。

### 1. 先实现业务场景，再识别公共能力

不要一开始就问“我要做一个多通用的 Runtime”。应该先问：

```text
这个场景要完成什么任务？
它有哪些 step？
step 之间交接什么 artifact？
失败后需要复盘什么？
是否需要恢复？
是否有高风险工具？
```

### 2. 优先使用 Runtime Core public API

场景代码应优先使用：

```python
from runtime_core.task import TaskContract, RuntimeState
from runtime_core.context import ContextBuilder, ContextPolicy
from runtime_core.memory import MemoryRecord, MemoryStore
from runtime_core.artifact import ArtifactRecord, ArtifactStore
from runtime_core.execution import MinimalRuntime, ToolPolicyChecker
from runtime_core.observability import TraceRecorder, FileCheckpointStore
```

如果场景频繁绕过 public API 访问内部模块，说明接口可能需要调整。

### 3. 记录使用摩擦

每个新场景都应记录：

- 哪些 Runtime API 顺手。
- 哪些字段不够用。
- 哪些 trace 不足以复盘。
- 哪些 artifact schema 难以表达。
- 哪些 tool policy 语义不自然。
- 哪些能力可能需要抽象。

### 4. 两个以上场景重复出现，再抽象进 core

单个场景的需求先留在场景目录中。只有当多个场景反复出现同类需求，才考虑抽入 Runtime Core。

例如：

| 多场景重复需求 | 可能抽象 |
|----------------|----------|
| 多个场景都需要 LLM structured call | LLM step adapter |
| 多个场景都需要 artifact 持久化 | Persistent ArtifactStore |
| 多个场景都需要多文件并行 | DAG / batch runner |
| 多个场景都需要人工审批 | Approval model |
| 多个场景都需要 provider 指标 | Model call trace schema |

### 5. 保持小核心

Runtime Core 的目标不是替代业务代码，而是提供公共支撑。它应该让场景更可靠，而不是让场景更难写。

最重要的判断仍然是：

```text
业务功能可以变化，
但上下文、记忆、状态、产物、trace 这些非功能能力会反复出现。
```

当前项目已经把这些能力识别出来，并完成了最小验证。后续更有价值的工作，是继续通过具体场景打磨它们，而不是一次性走向大而全的生产级框架。
