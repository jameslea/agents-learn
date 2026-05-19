# 阶段 1：Context Builder

## 目录

- [能力定位](#能力定位)
- [当前状态](#当前状态)
- [对应代码](#对应代码)
- [`runtime_core/context.py` 代码结构说明](#runtime_corecontextpy-代码结构说明)
  - [枚举层](#枚举层)
  - [数据模型层](#数据模型层)
  - [构造入口](#构造入口)
  - [关键私有方法](#关键私有方法)
  - [当前代码边界](#当前代码边界)
  - [Python 模块组织经验](#python-模块组织经验)
- [Demo 案例走读](#demo-案例走读)
  - [输入资料](#输入资料)
  - [选择结果](#选择结果)
  - [排除结果](#排除结果)
  - [输出字段怎么看](#输出字段怎么看)
- [当前选择规则](#当前选择规则)
- [当前压缩策略](#当前压缩策略)
- [当前防污染策略](#当前防污染策略)
- [当前治理能力](#当前治理能力)
- [核心字段说明](#核心字段说明)
- [Demo 行为](#demo-行为)
- [当前边界](#当前边界)
- [与计划的契合](#与计划的契合)

## 能力定位

Context Builder 验证一个核心判断：

```text
上下文不是聊天历史，而是当前 step 的工作视图。
```

它负责为当前 step 选择必要信息、压缩历史信息，并排除可能污染上下文的内容。

上下文工程的完整概念背景、主流设计理念和后续实现优先级，详见：[Agent 上下文工程：从 Prompt 拼接到可治理的工作视图](../../../docs/concepts/agent-context-engineering.md)。

## 当前状态

状态：`completed`

当前已经实现：

- `TaskContract`：最小任务入口契约。
- `RuntimeState`：最小任务状态模型。
- `ContextBuilder`：上下文选择、压缩和排除规则。
- `ContextBundle`：当前 step 的结构化上下文包。
- `selection_log`：上下文选择日志。
- `ContextPolicy`：上下文选择策略。
- `ContextCandidate`：统一候选模型。
- `ContextMetrics`：上下文构造指标。
- `ContextVisibility`：区分 `llm_visible`、`summary_only`、`runtime_only`。
- `ContextTrustLevel`：标记 system、tool、artifact、memory、external、untrusted 等信任等级。
- required context 检查：缺少必要 source 或 artifact type 时将 bundle 标记为 not ready。
- demo 脚本和测试。

## 对应代码

```text
runtime_core/contracts.py
runtime_core/state.py
runtime_core/context.py
scripts/run_context_demo.py
tests/test_context_builder.py
```

## `runtime_core/context.py` 代码结构说明

`context.py` 是阶段 1 的主要实现文件，代码可以按五层理解：

1. 枚举层：定义上下文来源、可见性和信任等级。
2. 数据模型层：定义 candidate、item、bundle、policy、metrics 等结构化对象。
3. 构造入口：`ContextBuilder.build()` 负责串联一次完整上下文构造。
4. 选择规则：私有方法负责最近 step、memory、candidate、预算和 required context 筛选。
5. 辅助函数：tag 规范化和过期时间判断。

### 枚举层

| 类 | 作用 |
|----|------|
| `ContextSourceType` | 标记上下文来自 goal、current step、step summary、artifact、memory 或 trace summary |
| `ContextVisibility` | 标记候选是否可进入模型上下文，还是只允许摘要或仅 Runtime 可见 |
| `ContextTrustLevel` | 标记来源信任等级，用于默认拦截不可信外部内容 |

这三类枚举构成 Context Builder 的基础治理维度：来源、可见性、可信度。

### 数据模型层

| 类 | 作用 |
|----|------|
| `ContextCandidate` | 统一候选模型，表示“可能进入上下文的信息” |
| `ArtifactCandidate` | artifact 摘要候选，当前不读取完整 artifact 正文 |
| `MemoryCandidate` | memory 摘要候选，阶段 2 会演进为正式 memory 模型 |
| `ContextItem` | 已通过筛选、最终进入上下文的条目 |
| `ContextSelection` | 每条候选的选择日志，记录进入或排除原因 |
| `ContextPolicy` | 上下文选择策略，集中管理预算、敏感信息、不可信来源和 required context |
| `ContextMetrics` | 上下文构造指标，用于测试、观测和后续 trace |
| `ContextBundle` | 最终输出的结构化上下文包 |

这里最重要的区分是：

```text
ContextCandidate 表示候选信息
ContextItem 表示最终进入上下文的信息
ContextSelection 表示候选为什么进入或被排除
ContextBundle 表示一次 step 可使用的完整上下文包
```

### 构造入口

`ContextBuilder.build()` 是这个文件的主流程，执行顺序如下：

1. 读取当前 `ContextPolicy`。
2. 将任务目标和当前 step 写入 `selection_log`，作为硬约束。
3. 从 `RuntimeState.steps` 选择最近已完成 step，并压缩为摘要。
4. 将 artifact、memory、trace summary 和外部传入候选统一收集为 `ContextCandidate`。
5. 对每个 candidate 执行可见性、敏感信息、信任等级、memory 专用规则和 tag 相关性筛选。
6. 执行整体字符预算裁剪。
7. 检查 required context 是否满足。
8. 生成 `ContextMetrics`。
9. 返回 `ContextBundle`。

从阅读代码的角度，建议先看 `build()`，再沿着它调用的私有方法向下读。

### 关键私有方法

| 方法 | 作用 |
|------|------|
| `_recent_step_summaries()` | 从状态中选择最近完成或失败的 step，排除当前 step |
| `_summarize_step()` | 将 step 压缩成短摘要 |
| `_collect_candidates()` | 把 artifact、memory、trace summary 和外部候选统一转成 `ContextCandidate` |
| `_select_candidate()` | 执行通用候选筛选，包括 visibility、sensitive、trust、tag 等规则 |
| `_select_memory()` | 执行 memory 专用筛选，包括 scope、tag、validated、confidence、expires_at |
| `_score_by_tags()` | 使用 tag overlap 计算最小相关性分数 |
| `_truncate()` | 控制单条上下文字符长度 |
| `_apply_context_budget()` | 控制整体上下文字符预算，并同步回写 `selection_log` |
| `_find_missing_required_context()` | 检查 required source id 和 artifact type 是否进入最终上下文 |
| `_build_metrics()` | 根据最终 items 和 selection log 生成观测指标 |

### 当前代码边界

`context.py` 当前有意保留了一些轻量实现，目的是先验证上下文工程的核心机制：

- tag overlap 只是最小相关性判断，不是最终检索方案。
- `MemoryCandidate` 只是阶段 1 过渡模型，后续会拆到 Memory / State 分层。
- `ArtifactCandidate` 只处理摘要和引用，后续 artifact schema / store 会独立实现。
- trace 只接收 summary，不接收完整 trace。
- 安全处理目前只做 sensitive / untrusted / runtime-only 拦截，还不是完整 prompt injection 防护。
- 预算按字符估算，后续可以替换为 token 估算。

因此阅读这个文件时，应把它理解为 Context Builder 的最小可运行核心，而不是完整生产级上下文系统。

### Python 模块组织经验

`context.py` 当前把 enum、候选模型、输出模型、策略、选择逻辑、预算控制和 builder 主流程放在同一个文件中。这在 Python 探索阶段可以接受，因为它减少了早期文件跳转成本；但如果继续堆叠，就会变成不利于理解和维护的“大杂烩模块”。

更合理的 Python 组织方式不是机械模仿 Java 的“一类一文件”，也不是把所有 Pydantic model 统一塞进 `models.py`。更好的粒度是按概念职责拆分模块，让文件名表达它在 Context Builder 中扮演的角色：

```text
runtime_core/context/
  source.py       # 上下文来源、可见性、信任等级
  candidate.py    # 候选上下文，包括 artifact / memory 过渡候选
  policy.py       # 上下文选择策略
  selection.py    # 选择日志和进入/排除原因
  output.py       # ContextItem、ContextBundle、ContextMetrics
  budget.py       # 单条截断和整体预算控制
  builder.py      # ContextBuilder 主流程
```

这个拆法的重点是“高内聚、低耦合”：一个文件承载一组强相关概念，而不是简单按技术类型堆叠。后续如果进入 hardening，可以沿着这个方向逐步拆分；当前阶段先保留单文件实现，避免在核心概念还未稳定时过早重构。

## Demo 案例走读

如果不想逐行阅读所有代码，可以先从 `scripts/run_context_demo.py` 入手。这个脚本构造了一个小场景：

```text
任务目标：围绕 Agent Runtime 的上下文治理写一份短研究报告
当前 step：基于证据表和项目写作偏好生成短报告大纲
step_tags：context、writing、research
required_artifact_types：evidence_table
```

这意味着 Context Builder 要为“写报告大纲”这一步准备上下文。它应该选择和写作、上下文治理、研究证据有关的信息，并排除部署说明、敏感信息、不可信外部信息和 Runtime 内部调试状态。

### 输入资料

demo 输入可以分成五类：

| 输入 | 示例 | 作用 |
|------|------|------|
| 任务契约 | `TaskContract(goal=...)` | 提供任务目标和成功标准 |
| 运行状态 | `RuntimeState.steps` | 提供已经完成的 step 摘要 |
| artifact 候选 | `artifact:evidence_table`、`artifact:deployment_notes` | 提供结构化产物摘要 |
| memory 候选 | `memory:project-output-style` 等 | 提供跨任务或项目经验 |
| 额外候选 | untrusted、sensitive、runtime-only candidate | 演示安全和可见性过滤 |

### 选择结果

运行 demo 后，最终进入 `ContextBundle.items` 的内容是：

| source_id | 为什么进入 |
|-----------|------------|
| `collect_sources` | 最近完成 step 摘要，帮助模型知道资料收集已经完成 |
| `draft_outline` | 最近完成 step 摘要，帮助模型知道已有大纲方向 |
| `artifact:evidence_table` | tag 与当前 step 匹配，且满足 required artifact type |
| `memory:project-output-style` | scope 匹配、tag 匹配、已验证、置信度足够 |
| `context-demo:research-mini:trace_summary` | trace summary 被允许进入，但只进入摘要 |

这里可以看到一个重要设计：任务目标和当前 step 会记录在 `selection_log` 中，并在 `ContextBundle.goal`、`ContextBundle.current_step` 中输出；它们不是普通 `items`，因为它们是当前上下文的硬约束。

### 排除结果

被排除的候选包括：

| source_id | 排除原因 | 对应治理能力 |
|-----------|----------|--------------|
| `external:untrusted-note` | 来源不可信，策略禁止进入模型上下文 | 信任边界 |
| `memory:sensitive-token-note` | 标记为 sensitive，策略禁止进入模型上下文 | 敏感信息拦截 |
| `runtime:debug-state` | `runtime_only`，只允许 Runtime 内部使用 | 可见性边界 |
| `artifact:deployment_notes` | tag 与当前 step 无关 | 相关性过滤 |
| `memory:old-provider-note` | memory tag 与当前 step 无关 | 记忆防污染 |
| `memory:unverified-rule` | memory 未验证 | 记忆可信度控制 |

这比只看最终 prompt 更有价值，因为 `selection_log` 不仅告诉我们“用了什么”，还告诉我们“为什么不用某些信息”。

### 输出字段怎么看

demo 输出的关键字段可以这样读：

| 字段 | 阅读方式 |
|------|----------|
| `items` | 真正进入当前 step 工作上下文的内容 |
| `selection_log` | 全部候选的进入或排除原因 |
| `metrics.item_count` | 最终进入 `items` 的数量 |
| `metrics.included_count` | selection log 中被标记为 included 的数量，包括 goal 和 current step |
| `metrics.excluded_count` | 被排除候选数量 |
| `metrics.source_type_breakdown` | 最终上下文中各类来源的分布 |
| `metrics.budget_used_ratio` | 当前上下文预算使用比例 |
| `ready` | required context 是否满足 |
| `missing_required_context` | 如果 `ready=false`，这里说明缺少什么 |

当前 demo 的结果中：

```text
item_count = 5
included_count = 7
excluded_count = 6
ready = true
missing_required_context = []
```

`item_count` 和 `included_count` 不相等是正常的：`goal` 和 `current_step` 是硬约束，会记录在 `selection_log`，但不会重复放入 `items`。

### 一句话理解 demo

```text
Context Builder 不是把所有资料塞给模型，
而是把当前 step 需要的资料选出来，
把不相关、不可信、敏感、未验证和 Runtime-only 的资料挡在外面，
并把每个选择写成可复盘的 selection_log。
```

## 当前选择规则

| 信息类型 | 进入条件 |
|----------|----------|
| 任务目标 | 始终进入 |
| 当前 step | 始终进入 |
| 最近 step 摘要 | 保留最近 N 条完成或失败的 step |
| artifact | tag 与当前 step tag 匹配 |
| memory | scope 匹配、tag 匹配、已验证、置信度达标、未过期 |
| trace | 只进入摘要，不进入原始 trace |
| sensitive candidate | 默认不进入模型上下文 |
| untrusted candidate | 默认不进入模型上下文 |
| runtime-only candidate | 不进入模型上下文 |

## 当前压缩策略

- step 只保存摘要，不保存完整历史。
- artifact 只放摘要、类型、路径和 tag，不读取完整正文。
- memory 只放摘要内容和基础元数据。
- trace 只放摘要，不放原始 trace。
- 单条 item 和整体 context 都有字符预算。

## 当前防污染策略

当前会排除：

- tag 与当前 step 不相关的 artifact。
- tag 与当前 step 不相关的 memory。
- 未验证 memory。
- 低置信 memory。
- 已过期 memory。
- 超过 context 字符预算的信息。

排除原因会写入 `ContextSelection.reason`。

## 当前治理能力

| 能力 | 当前实现 |
|------|----------|
| 策略控制 | `ContextPolicy` 管理预算、memory 置信度、trace 摘要、敏感和不可信候选策略 |
| 统一候选 | `ContextCandidate` 可承载 state、artifact、memory、trace、resource 等候选来源 |
| 可见性 | `ContextVisibility` 区分 `llm_visible`、`summary_only`、`runtime_only` |
| 信任等级 | `ContextTrustLevel` 标记 system、user、tool、artifact、memory、external、untrusted |
| 敏感拦截 | `sensitive=True` 且策略开启时不会进入模型上下文 |
| required context | 支持 `required_source_ids` 和 `required_artifact_types` |
| 指标 | `ContextMetrics` 输出 item 数、排除数、source type 分布、预算比例等 |

## 核心字段说明

文档只记录理解代码所需的核心字段。更完整的字段说明见 `runtime_core/context.py` 中的类 docstring 和 `Field(description=...)`。

### ContextCandidate

`ContextCandidate` 是统一候选模型，表示“可能进入上下文的信息”。

| 字段 | 说明 |
|------|------|
| `source_type` | 候选来源类型，例如 artifact、memory、trace summary |
| `source_id` | 候选唯一标识，用于 selection log、required context 和 trace 关联 |
| `content` | 候选正文或摘要 |
| `tags` | 与当前 step tags 匹配，用于相关性筛选 |
| `visibility` | 可见性：`llm_visible`、`summary_only`、`runtime_only` |
| `trust_level` | 信任等级：system、tool、artifact、memory、external、untrusted |
| `sensitive` | 是否包含敏感内容，默认策略会排除 |
| `artifact_type` | 如果候选来自 artifact，用于 required artifact type 检查 |
| `scope` / `confidence` / `validated` / `expires_at` | 主要用于 memory 筛选 |

### ContextPolicy

`ContextPolicy` 表示“当前 step 如何选择上下文”。

| 字段 | 说明 |
|------|------|
| `max_recent_steps` | 最近 step 摘要保留数量 |
| `max_item_chars` | 单条上下文最大字符数 |
| `max_context_chars` | 整体上下文字符预算 |
| `min_memory_confidence` | memory 进入上下文的最低置信度 |
| `include_trace_summary` | 是否允许 trace summary 进入上下文 |
| `allow_untrusted_external_context` | 是否允许不可信候选进入模型上下文 |
| `exclude_sensitive` | 是否排除敏感候选 |
| `required_source_ids` | 当前 step 必须具备的 source id |
| `required_artifact_types` | 当前 step 必须具备的 artifact type |

### ContextBundle

`ContextBundle` 是 Context Builder 的输出。

| 字段 | 说明 |
|------|------|
| `items` | 最终进入上下文的条目 |
| `selection_log` | 每条候选进入或排除的原因 |
| `metrics` | 上下文构造指标 |
| `ready` | required context 是否满足 |
| `missing_required_context` | 缺失的必要上下文 |
| `blocked_reason` | `ready=False` 时的阻塞原因 |

### ContextMetrics

`ContextMetrics` 用于观察上下文选择过程。

| 字段 | 说明 |
|------|------|
| `total_chars` | 估算上下文字符数 |
| `item_count` | 最终进入上下文的 item 数 |
| `included_count` / `excluded_count` | selection log 中进入和排除的数量 |
| `source_type_breakdown` | 按来源类型统计进入项 |
| `budget_used_ratio` | 字符预算使用比例 |
| `sensitive_excluded_count` | 因敏感标记被排除的候选数量 |
| `untrusted_excluded_count` | 因不可信被排除的候选数量 |
| `missing_required_count` | 缺失 required context 的数量 |

## Demo 行为

运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_context_demo.py
```

默认输出是面向阅读的过程摘要，包含：

- `[Task]`：当前任务、当前 step 和 `ready` 状态。
- `[Selected Context Items]`：最终进入上下文的内容。
- `[Included Decisions]`：被选中的上下文及原因。
- `[Excluded Decisions]`：被排除的候选及原因。
- `[Metrics]`：上下文大小、类型分布、预算占比和排除统计。

如果需要查看完整 `ContextBundle` JSON，可以运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_context_demo.py --format json
```

默认文本输出可以观察到：

- `artifact:evidence_table` 被选中。
- `artifact:deployment_notes` 因 tag 不相关被排除。
- `memory:project-output-style` 被选中。
- `memory:old-provider-note` 因 tag 不相关被排除。
- `memory:unverified-rule` 因未验证被排除。
- `external:untrusted-note` 因不可信被排除。
- `memory:sensitive-token-note` 因 sensitive 被排除。
- `runtime:debug-state` 因 runtime-only 被排除。
- trace 只进入摘要。
- `metrics` 展示上下文大小、类型分布、预算占比和排除统计。

## 当前边界

当前阶段暂不实现：

- 向量检索。
- LLM 自动摘要。
- 长期 memory store。
- artifact store。
- prompt injection 检测。
- 完整敏感信息脱敏。
- 多轮对话历史管理。
- 上下文版本和 diff。

这些能力属于后续阶段或更高层 Runtime 能力。

## 与计划的契合

| 问题 | 当前回答 |
|------|----------|
| 上下文怎么选 | 按目标、当前 step、step 摘要、artifact tag、memory scope / tag / confidence / expires_at 选择 |
| 上下文怎么压缩 | 历史 step、artifact、memory、trace 都只进入摘要或引用 |
| 上下文怎么防污染 | selection log 记录无关、未验证、低置信、过期、敏感、不可信、runtime-only 和超预算信息的排除原因 |
