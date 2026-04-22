# 阶段 15：生产级 Agent 工程

> 状态：✅ 已完成

本阶段把前面所有 Demo 中的 Agent 思想升级为可上线系统需要考虑的工程能力，重点探讨了评估体系（RAGAS）、可观测性（Trace/Langfuse）和安全护栏（Guardrails）三大生产核心议题。

---

## 核心学习成果

- RAGAS 评估框架的四维指标：Faithfulness、Answer Relevance、Context Precision、Context Recall
- LLM-as-a-Judge：用顶级模型按评分准则给 Agent 输出打分
- 可观测性：Trace、Span、Token 追踪，Langfuse / LangSmith / Arize Phoenix
- 安全护栏：内容审计、PII 脱敏、结构校验
- 生产级工程清单：重试、降级、超时、熔断、人工接管
- 详见：[concept.md](./concept.md)、[ragas_deep_dive.md](./ragas_deep_dive.md) 与 [summary.md](./summary.md)

---

## 代码与文档

| 文件 | 说明 |
|---|---|
| `guardrails_demo.py` | 生产级护栏示例（脱敏、审计、结构校验） |
| `concept.md` | 评估、可观测性与护栏的核心概念 |
| `ragas_deep_dive.md` | RAGAS 评估框架深度解析 |

> 本阶段以理论总结和工程规范为主，无可运行代码。

---

## 🎊 全程结项

> 本仓库记录了从基础 Prompt 到复杂多 Agent 系统的全演进过程。15 个阶段，构成了一套完整的智能体架构师知识图谱。
> **掌握底层逻辑，驱动 AI 未来。**

---

## 阶段总结

详见 [summary.md](./summary.md)。
