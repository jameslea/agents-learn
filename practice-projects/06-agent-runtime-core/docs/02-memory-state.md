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

状态：`pending`

阶段 1 中已经有最小 `RuntimeState`，但还没有正式 `MemoryRecord` 和正式 `Artifact`。

## 计划实现

预计新增或整理：

```text
runtime_core/memory.py
runtime_core/artifact.py
tests/test_memory_state_boundaries.py
scripts/run_memory_state_demo.py
```

## 设计要点

| 类型 | 职责 | 示例 |
|------|------|------|
| `RuntimeState` | 当前任务进度 | 当前执行到 `draft_report`，已完成 `collect_sources` |
| `MemoryRecord` | 跨任务经验或偏好 | 用户偏好 Markdown 表格；某类任务应先生成 evidence table |
| `Artifact` | 可验证、可交接的结构化产物 | `research_plan.json`、`evidence_table.json`、`review_result.json` |

## 需要验证的问题

- memory 是否可以带来源、scope、tag、confidence、validated、expires_at。
- state 是否只保存任务进度，而不保存长期经验。
- artifact 是否通过 schema 保存，不混入 state 或 memory。
- Context Builder 是否能分别引用 state、memory 和 artifact。

## 验收标准

- 三类数据能分别创建、保存和读取。
- demo 能展示三者如何被 Context Builder 使用。
- 文档中明确说明三者边界，避免混用。

## 当前边界

本阶段不做：

- 向量数据库。
- 自动长期记忆提取。
- 多用户记忆隔离。
- 复杂 memory ranking。

这些能力需要等边界稳定后再引入。
