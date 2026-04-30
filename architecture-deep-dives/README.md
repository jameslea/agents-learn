# AI Agent 从玩具到工业级：生产环境生存指南 (Architecture Deep Dives)

> **关于本指南**：
> 如果本仓库的前 15 个阶段是教你“如何造一辆车”，那么本指南则是教你**“如何在极端恶劣的路况下飙车而不翻车”**。
> 这里没有简单的 API 调用 Demo，只有深入到底层原理、数据清洗、架构设计与安全攻防的硬核架构剖析。

---

## 🗺️ 架构师必修课全景图

本指南分为四大核心章节，直击生产环境中最致命的痛点：

### 🧱 Chapter 1: 模型底层原理与定向优化 (Model Internals)
*不要把大模型当黑盒，榨干它的每一滴性能。*
*   📄 [01-sft-vs-dpo.md](./chapter1-model-internals/01-sft-vs-dpo.md) - **微调技术**：详解 SFT（格式矫正）与 DPO（逻辑偏好对齐）的本质区别与实战避坑。
*   📄 [02-prompt-caching.md](./chapter1-model-internals/02-prompt-caching.md) - **上下文工程**：剖析“中间失忆”现象，以及如何利用 Prompt Caching（提示词缓存）给 Agent 提速降本。
*   📄 [03-inference-and-quantization.md](./chapter1-model-internals/03-inference-and-quantization.md) - **高性能推理**：详解 vLLM 的 PagedAttention 并发魔法与量化对 Agent 智力的影响。
*   📄 [04-mac-vs-linux-hardware.md](./chapter1-model-internals/04-mac-vs-linux-hardware.md) - **硬件抉择**：深度剖析 Mac 统一内存（GGUF/MLX）与 Linux 服务器独显（AWQ）的架构鸿沟。

### 📊 Chapter 2: 深度数据工程与 Agentic RAG (Advanced Data)
*解决“Garbage in, Garbage out”，重塑 Agent 的知识摄入管道。*
*   📄 [01-rerank-and-query-expansion.md](./chapter2-data-engineering/01-rerank-and-query-expansion.md) - **高级检索**：抛弃裸奔的向量检索，引入 Rerank (交叉编码器) 与 Query Expansion (HyDE改写)。
*   📄 [02-pdf-table-etl.md](./chapter2-data-engineering/02-pdf-table-etl.md) - **非结构化 ETL**：使用视觉大模型解析复杂 PDF，以及处理表格的“摘要包裹法”。
*   📄 [03-graphrag-limits.md](./chapter2-data-engineering/03-graphrag-limits.md) - **图谱增强**：拆解 GraphRAG（微软架构），解决传统 RAG 无法完成的“跨文档全局逻辑推理”难题。

### ⚙️ Chapter 3: 分布式 Agent 架构与底层工程 (Systems & Infra)
*让 Agent 在网络闪断和复杂逻辑流转中稳定运行。*
*   📄 [01-checkpoint-and-actor-model.md](./chapter3-distributed-system/01-checkpoint-and-actor-model.md) - **架构护航**：异步解耦与消息队列选型、LangGraph/Temporal Checkpoint 断点续传、多 Agent 协调四种模式对比（编排器/黑板/Actor/消息总线），以及副作用重放和确定性约束等核心陷阱。

### 🛡️ Chapter 4: 评估体系与全链路安全防御 (Evaluation & Security)
*上线生产环境前的最后两道生死门槛。*
*   📄 [01-llm-judge-and-guardrails.md](./chapter4-evaluation-security/01-llm-judge-and-guardrails.md) - **测评与防线**：使用 LLM-as-a-Judge 自动化量化测试指标（忠实度、工具成功率）；Prompt Injection 攻击手法演进与最小权限原则，以及多层防御护栏。

---
*版权所有：本项目内容系真实业务沉淀，欢迎 Star 与探讨！*
