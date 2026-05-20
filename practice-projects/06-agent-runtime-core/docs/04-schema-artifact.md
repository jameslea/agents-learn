# 阶段 4：Schema Artifact 交接

## 目录

- [能力定位](#能力定位)
- [当前状态](#当前状态)
- [实现文件](#实现文件)
- [核心对象](#核心对象)
- [最小场景](#最小场景)
- [交接语义](#交接语义)
- [验证方式](#验证方式)
- [Demo 输出说明](#demo-输出说明)
- [核心概念](#核心概念)
- [经验教训](#经验教训)
- [当前边界](#当前边界)

## 能力定位

Schema Artifact 要验证 Agent 或 step 之间通过结构化产物交接，而不是通过自由文本交接。

自由文本适合阅读，但不适合作为稳定接口。结构化 artifact 可以校验、追踪、复盘，也更适合被下游 step 消费。阶段 4 的重点不是做完整 artifact 平台，而是先验证一个最小闭环：

```text
生成 artifact -> schema 校验 -> 保存 -> 下游按 schema 读取 -> 继续生成下一个 artifact
```

## 当前状态

状态：`completed`

阶段 2 已经有 `ArtifactRecord`，但它主要用于记录结构化产物和给 Context Builder 提供摘要引用。阶段 4 在此基础上补齐：

- 具体 schema。
- artifact store。
- 保存前校验。
- 下游消费时的 schema 检查。
- 可运行 handoff demo。

## 实现文件

相对代码根目录：`practice-projects/06-agent-runtime-core/`

```text
runtime_core/artifact/
scenarios/research_mini/schemas.py
runtime_core/artifact/store.py
scripts/run_artifact_handoff_demo.py
tests/test_schema_artifact.py
```

## 核心对象

| 对象 | 职责 |
|------|------|
| `ArtifactRecord` | 通用 artifact 记录，保存 id、type、summary、schema、producer、payload 和 metadata |
| `EvidenceTable` | Research step 产出的证据表 schema |
| `DraftReport` | Writer step 消费证据表后产出的报告草稿 schema |
| `ReviewResult` | Reviewer step 消费草稿后产出的审查结果 schema |
| `ArtifactStore` | 内存版 artifact store，负责保存、读取和 schema 校验 |
| `ArtifactValidationResult` | 描述一次校验是否通过，以及失败原因 |
| `ArtifactValidationError` | artifact 缺失、schema 不匹配或 payload 不合格时抛出 |

## 最小场景

```text
Research Step -> EvidenceTable artifact
Writer Step -> 读取 EvidenceTable payload -> DraftReport artifact
Reviewer Step -> 读取 DraftReport payload -> ReviewResult artifact
```

下游 step 不读取上游自由文本，只通过 artifact id 和 schema name 读取结构化 payload。

## 交接语义

1. 上游 step 先构造 Pydantic schema model。
2. `ArtifactStore.save_model()` 将 schema model 转成 `ArtifactRecord.payload`。
3. 保存前根据 `schema_name` 执行 schema 校验。
4. 校验通过后，`ArtifactRecord.validated` 被标记为 `True`。
5. 下游 step 使用 `load_payload(artifact_id, schema_name=...)` 读取 payload。
6. 如果 artifact 不存在、schema 不匹配、未验证或 payload 不合格，读取失败并返回明确原因。
7. 下游 step 生成新的 schema artifact，并在 metadata 中记录 `consumed_artifact_ids`。

正式 trace 还没有接入。当前阶段只在 metadata 中记录 artifact 消费关系，阶段 5 再把生成和消费事件写入 trace。

## 验证方式

运行 demo：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_artifact_handoff_demo.py
```

输出 JSON：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_artifact_handoff_demo.py --format json
```

运行测试：

```bash
python3 -m pytest practice-projects/06-agent-runtime-core/tests/test_schema_artifact.py
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

## Demo 输出说明

demo 会展示三类信息：

- `Handoff artifacts`：三个 artifact 的 id、schema、producer、payload key 和消费关系。
- `Consumption chain`：writer 和 reviewer 分别读取了哪个上游 artifact。
- `Invalid artifact check`：故意保存缺少 `rows` 的 `EvidenceTable`，验证 schema error 是否可见。

典型错误示例：

```text
rows: Field required
```

## 核心概念

- Artifact 是 step 之间的结构化接口，不只是上下文中的一段文字。
- Schema name 是 artifact 消费方的契约；下游必须声明自己期望读取的 schema。
- `ArtifactRecord.summary` 用于上下文引用，`ArtifactRecord.payload` 用于结构化消费，两者不能混用。
- `ArtifactRecord.validated` 默认是 `False`；`validated=True` 表示 payload 已经通过 schema 或人工校验，可以被下游消费。
- 消费关系应被记录下来，当前使用 `metadata.consumed_artifact_ids`，后续进入 trace。

## 经验教训

- 只有 `ArtifactRecord` 还不够；如果没有 schema 校验，下游仍然无法相信 payload 的字段稳定。
- 下游读取时也要检查 schema，不能只依赖保存时校验，否则 schema 错配会在更深处变成业务错误。
- artifact store 先做内存版更合适，便于验证边界；持久化应等 trace、checkpoint 和 artifact 的存储关系更清楚后再统一考虑。
- Context Builder 继续只引用 summary / path / schema，不读取完整 payload，这一点可以防止上下文膨胀。

## 当前边界

本阶段不做：

- 持久化 artifact store。
- 通用 artifact registry。
- 跨项目 artifact 共享。
- 大文件和二进制产物管理。
- artifact schema 版本迁移。
- 正式 trace 写入。

阶段 4 只验证“结构化交接”这个核心动作是否成立。
