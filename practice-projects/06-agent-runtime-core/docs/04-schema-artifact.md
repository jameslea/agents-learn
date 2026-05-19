# 阶段 4：Schema Artifact 交接

## 能力定位

Schema Artifact 要验证 Agent 或 step 之间通过结构化产物交接，而不是通过自由文本交接。

自由文本适合阅读，但不适合作为稳定接口。结构化 artifact 可以校验、追踪、复盘，也更适合被下游 step 消费。

## 当前状态

状态：`pending`

当前只有 `ArtifactCandidate`，它只是 Context Builder 的候选摘要，不是正式 artifact schema。

## 计划实现

预计新增：

```text
runtime_core/artifact.py
runtime_core/artifact_store.py
scripts/run_artifact_handoff_demo.py
tests/test_schema_artifact.py
```

## 最小场景

```text
Research Step -> EvidenceTable artifact
Writer Step -> 读取 EvidenceTable 生成 DraftReport
Reviewer Step -> 读取 DraftReport 生成 ReviewResult
```

## 建议 artifact

| Artifact | 字段示例 |
|----------|----------|
| `EvidenceTable` | claim、source、confidence、notes |
| `DraftReport` | title、sections、evidence_refs |
| `ReviewResult` | score、issues、required_changes、passed |

## 需要验证的问题

- 下游 step 是否只读取 artifact，而不是读取上游自由文本。
- artifact 缺字段或不合格时是否能失败并记录原因。
- artifact 是否能被 Context Builder 引用为摘要，而不是全文塞入上下文。

## 验收标准

- 至少 2-3 个 Pydantic artifact schema。
- artifact validator 能发现缺字段或不合格数据。
- demo 能展示 artifact 生成、保存、读取和下游消费。

## 当前边界

本阶段不做：

- 通用 artifact registry。
- 跨项目 artifact 共享。
- 大文件和二进制产物管理。
- 复杂版本迁移。

先验证“结构化交接”这个核心动作是否成立。
