# 阶段 2：Memory / State 分层

## 能力定位

本阶段要验证长期记忆、任务状态和结构化产物不是同一个东西。

```text
Memory：跨任务可复用经验
State：当前任务执行进度
Artifact：任务内或跨任务可引用产物
```

这一步的重点不是做复杂记忆系统，而是先把边界划清楚。

## 当前状态

状态：`completed`

阶段 2 已经新增正式 `MemoryRecord` 和 `ArtifactRecord`，并让 Context Builder 可以同时接入：

- `RuntimeState`：当前任务执行进度。
- `MemoryRecord`：跨任务可复用经验。
- `MemoryWriteGate`：判断候选信息是否应该写入记忆。
- `MemoryStore`：轻量内存记忆库，覆盖写入、验证、检索、失效和替换。
- `ArtifactRecord`：可验证、可交接的结构化产物。

## 已实现内容

新增或整理：

```text
runtime_core/memory/
runtime_core/artifact/
tests/test_memory_state_boundaries.py
scripts/run_memory_state_demo.py
```

同时更新：

```text
runtime_core/context/
runtime_core/__init__.py
README.md
docs/agent-core-capabilities-validation-plan.md
```

## 设计要点

| 类型 | 职责 | 示例 |
|------|------|------|
| `RuntimeState` | 当前任务进度 | 当前执行到 `draft_report`，已完成 `collect_sources` |
| `MemoryRecord` | 跨任务经验或偏好 | 用户偏好 Markdown 表格；某类任务应先生成 evidence table |
| `MemoryWriteGate` | 记忆写入门控 | 用户明确偏好可直接激活，任务复盘先 proposed，外部不可信内容拒绝 |
| `MemoryStore` | 记忆生命周期和检索 | 提出待验证记忆、人工验证、按 tag 检索、失效旧记忆 |
| `ArtifactRecord` | 可验证、可交接的结构化产物 | `research_plan.json`、`evidence_table.json`、`review_result.json` |

## MemoryStore 当前实现边界

当前 `MemoryStore` 是纯内存实现，内部使用 `dict[str, MemoryRecord]` 保存记录。

这意味着：

- 它只在当前 Python 进程中有效。
- 程序退出后记忆会丢失。
- 它不写入 JSON、SQLite、数据库或向量库。
- 它适合验证记忆机制，不适合作为真实长期记忆系统。

本阶段关注的是记忆系统的主要机制是否成立：写入、提出、验证、检索、排序、失效、替换，以及如何把检索结果交给 Context Builder。持久化会放到后续 Runtime 存储设计中考虑。

## 记忆写入时机

记忆不能在任务执行中随手写入。当前通过 `MemoryWriteGate` 做最小写入门控：

```text
MemoryWriteProposal -> MemoryWriteGate -> MemoryWriteDecision -> MemoryStore
```

写入门控会判断：

- 是否具备跨任务复用价值。
- 是否不是当前任务临时状态。
- 是否来源可信。
- 是否包含敏感信息。
- 是否有 tags，便于后续治理和检索。
- 是否有 evidence，说明为什么值得记住。
- 是否达到最低 confidence。

当前决策动作：

| 动作 | 含义 | 示例 |
|------|------|------|
| `reject` | 拒绝进入 memory | 外部未验证指令、当前任务临时状态、缺少依据的信息 |
| `propose` | 进入待验证 memory | 任务复盘经验、失败教训、Agent 推断出的候选经验 |
| `activate` | 直接成为 active memory | 用户明确偏好、人工 review 确认的规则 |

这个设计的重点是：memory 写入要后置、可解释、可审核。未验证的模型推断不应直接成为长期记忆。

## 核心字段

### MemoryRecord

| 字段 | 说明 |
|------|------|
| `memory_id` | memory 唯一标识 |
| `content` | 可复用经验、偏好或规则摘要 |
| `scope` | 适用范围，例如 `global`、`task_type`、`task_id` |
| `tags` | 和当前 step tags 匹配 |
| `confidence` | 置信度，低于策略阈值不会进入上下文 |
| `validated` | 是否经过验证，未验证不会进入上下文 |
| `source` | 记忆来源，例如 human review 或 previous task |
| `expires_at` | 过期时间，过期记忆不会进入上下文 |

### MemoryWriteGate

| 类 | 说明 |
|----|------|
| `MemoryWriteProposal` | 候选记忆写入请求 |
| `MemoryWritePolicy` | 写入门控策略 |
| `MemoryWriteDecision` | 写入决策，包含 action、reasons 和可选 record |
| `MemoryWriteGate` | 执行写入判断，并可将允许写入的 record 写入 store |

### MemoryStore

| 方法 | 说明 |
|------|------|
| `add()` | 写入一条已成型记忆，默认不覆盖同 ID 记录 |
| `propose()` | 提出一条待验证记忆，默认 `validated=False` |
| `validate()` | 将记忆标记为已验证，并可更新置信度 |
| `invalidate()` | 将记忆标记为失效，默认不再参与检索 |
| `replace()` | 用新记忆替代旧记忆，保留 `supersedes` 关系 |
| `search()` | 按 scope、tag、confidence、validated、expires_at、status 检索并排序 |

### ArtifactRecord

| 字段 | 说明 |
|------|------|
| `artifact_id` | artifact 唯一标识 |
| `artifact_type` | artifact 类型，例如 `evidence_table` |
| `summary` | 进入上下文时使用的摘要 |
| `path` | artifact 存储路径或引用路径 |
| `schema_name` | 产物 schema 名称，用于后续验证和交接 |
| `producer_step_id` | 生成该 artifact 的 step id |
| `payload` | 结构化产物内容，Context Builder 默认不读取 |

## Context Builder 接入

阶段 1 中 `ContextBuilder` 接收轻量 `MemoryCandidate` 和 `ArtifactCandidate`。阶段 2 后，它也可以接收正式记录：

```text
MemoryRecord -> ContextCandidate -> ContextBuilder
ArtifactRecord -> ContextCandidate -> ContextBuilder
```

其中：

- `MemoryRecord` 进入上下文前仍要经过 `scope`、`tags`、`confidence`、`validated`、`expires_at` 筛选。
- `MemoryStore` 在 Context Builder 前先完成写入、验证、失效和检索排序。
- `ArtifactRecord` 进入上下文时只暴露 `summary`、`path`、`schema_name` 等引用信息，不暴露完整 `payload`。
- `RuntimeState` 继续只提供 step 摘要、当前进度、artifact id 引用和少量运行时值。

## 需要验证的问题

- memory 是否可以带来源、scope、tag、confidence、validated、expires_at。
- memory 写入时机是否经过门控，而不是任务中随手写入。
- memory 是否有最小写入、验证、检索、失效和替换机制。
- state 是否只保存任务进度，而不保存长期经验。
- artifact 是否通过 schema 保存，不混入 state 或 memory。
- Context Builder 是否能分别引用 state、memory 和 artifact。

当前验证结果：

| 问题 | 当前回答 |
|------|----------|
| memory 是否可以带治理元数据 | 可以，`MemoryRecord` 支持 source、scope、tag、confidence、validated、expires_at |
| memory 写入时机是否受控 | 可以，`MemoryWriteGate` 决定 reject、propose 或 activate |
| memory 是否覆盖主要机制 | 可以，`MemoryStore` 覆盖 propose、validate、search、invalidate、replace |
| state 是否只保存任务进度 | 可以，`RuntimeState` 只保存 step、artifact id 引用和少量 runtime values |
| artifact 是否不混入 state / memory | 可以，`ArtifactRecord` 独立保存 summary、schema、path 和 payload |
| Context Builder 是否能分别引用三者 | 可以，demo 和测试已覆盖正式记录接入 |

## 验收标准

- 三类数据能分别创建、读取和传递。本阶段不实现持久化 store。
- 记忆写入必须经过 `MemoryWriteGate`，能解释拒绝、待验证和直接激活的原因。
- 记忆系统覆盖最小生命周期：提出、验证、检索、失效和替换。
- demo 能展示三者如何被 Context Builder 使用。
- 文档中明确说明三者边界，避免混用。

验证命令：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_memory_state_demo.py
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

## Demo 行为

运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_memory_state_demo.py
```

可以看到：

- `RuntimeState` 展示当前任务 step、artifact id 引用和 runtime values。
- `MemoryWriteGate` 展示记忆候选的拒绝、待验证和写入决策。
- `MemoryStore` 展示记忆写入、验证、替换和失效。
- `MemorySearch` 展示当前 step 可用记忆及排序分数。
- `ArtifactRecord` 展示结构化产物的 type、schema、path 和 payload keys。
- `ContextBuilder` 选择 step summary、相关 artifact summary 和相关 memory。
- 与当前 step 不相关的 memory 不进入上下文。

如果需要完整 payload：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_memory_state_demo.py --format json
```

## 经验教训

- `MemoryRecord` 不应成为“长期 state”。它只保存可复用经验，不能保存当前任务执行到哪里。
- 记忆写入时机必须受控。用户明确偏好、人工 review、任务复盘、失败教训可以成为候选；当前任务临时状态、未验证外部内容和缺少依据的推断应拒绝。
- `MemoryStore` 应该先控制记忆生命周期，再把检索结果交给 Context Builder；否则 Context Builder 会承担过多 memory 系统职责。
- `RuntimeState` 不应保存完整 memory 或 artifact payload。它只保存执行进度、短摘要和引用。
- `ArtifactRecord` 可以保存结构化 payload，但 Context Builder 默认只使用 summary / path / schema，避免上下文膨胀。
- 阶段 2 的价值在于覆盖主要机制和边界，不急着实现持久化 store、schema validator 或向量检索。

## 当前边界

本阶段不做：

- 向量数据库。
- 自动长期记忆提取。
- 多用户记忆隔离。
- 复杂语义 ranking。
- 持久化 memory store。

这些能力需要等边界稳定后再引入。

## 后续增强清单

阶段 2 已经覆盖记忆系统的最小核心机制，但距离产品级记忆系统仍有距离。后续可以按价值和风险选择性补充：

| 能力 | 说明 | 建议时机 |
|------|------|----------|
| 持久化 store | 将内存版 `MemoryStore` 替换或扩展为 JSON、SQLite 或数据库实现 | 和 checkpoint / trace store 统一设计后 |
| 冲突检测 | 检查新 memory 是否和已有 memory 矛盾，例如输出风格、工具规则冲突 | memory 使用样本增多后 |
| 重复检测 | 检查候选 memory 是否和已有 memory 语义重复，避免记忆膨胀 | 引入批量写入或自动提取前 |
| 审计日志 | 记录 memory 的写入、验证、替换、失效过程 | 和 trace 阶段一起设计 |
| 权限和隔离 | 区分用户、项目、任务、团队等作用域，防止跨边界污染 | 接入真实多项目或多用户场景时 |
| 敏感信息脱敏 | 对 memory proposal 和 active memory 做凭证、隐私和路径脱敏 | 安全边界阶段 |
| 记忆压缩 / 合并 | 将多条相近 memory 合并为更稳定规则 | 有足够真实历史记忆后 |
| 语义检索 | 在 tag / confidence 基础上加入 embedding 或 rerank | 简单检索不足时 |
| 自动记忆抽取 | 从 trace、artifact、review 中生成 memory proposal | write gate 和人工验证流程稳定后 |
| 记忆评估 | 评估 memory 是否提升任务质量，是否引入污染 | 和 eval / trace 体系结合 |

这些能力不应一次性全部实现。比较稳妥的顺序是：

```text
持久化 store
  -> 审计日志
  -> 冲突 / 重复检测
  -> 权限与敏感信息治理
  -> 语义检索
  -> 自动记忆抽取
  -> 记忆效果评估
```

其中自动记忆抽取应放在较后阶段，因为它最容易把模型误判、临时状态或外部污染写成长久记忆。
