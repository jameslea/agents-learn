# Concepts 文档说明

> 更新时间：2026-05-20
>
> 本目录用于沉淀 Agent、RAG、模型运行时和多模态能力相关的概念、方法论和选型研究。这里的文档不是项目操作手册，而是为后续实践项目提供理论背景、架构判断和工程决策依据。

## 文档列表

| 文档 | 标题 | 内容简述 |
|------|------|----------|
| [agent-architectures-react-plan-reflect.md](./agent-architectures-react-plan-reflect.md) | Agent 核心架构模式深度解析：ReAct、Plan & Execute 与 Reflection | 解释 ReAct、Plan and Execute、Reflection 三种 Agent 架构模式的核心差异、优缺点和融合方式，为理解复杂 Agent 工作流打基础。 |
| [agent-design-methodology.md](./agent-design-methodology.md) | Agent 设计方法论：从角色实验到可控系统 | 总结多 Agent 实践后的设计方法，强调 workflow、state、artifact、tool、eval 优先于角色命名，帮助判断一个任务是否真的需要 Agent。 |
| [agent-core-structure.md](./agent-core-structure.md) | Agent 系统核心结构：模型、工具、编排、状态与运行时 | 结合主流研究、厂商白皮书、框架文档和当前项目启发，先从 Model / Tools / Orchestration 解释 Agent 一阶结构，再梳理类型谱系、上下文、记忆、artifact、trace 和 Runtime Core。 |
| [agent-reading-roadmap.md](./agent-reading-roadmap.md) | Agent 深度学习阅读路线：经典文章、公开论文与工程文档 | 在当前多轮 Agent 实践和 Runtime Core 探索基础上，整理后续扩大学习范围的经典文章、公开论文、工程文档和阅读顺序，并说明它们与上下文、记忆、工具、状态、artifact、trace 和 runtime 的关系。 |
| [agent-development-capability-and-interview.md](./agent-development-capability-and-interview.md) | Agent 开发能力定位与面试准备 | 说明读完 Agent 必读资料并结合当前实践后，大致能达到什么工程能力，面试 Agent 开发岗时如何定位，以及还需要继续强化哪些能力。 |
| [agent-context-engineering.md](./agent-context-engineering.md) | Agent 上下文工程：从 Prompt 拼接到可治理的工作视图 | 专题讨论 Agent 上下文类型分层、生命周期、Context Builder、上下文污染治理、上下文评估和后续 Runtime Core 实现优先级。 |
| [agent-theory-to-practice.md](./agent-theory-to-practice.md) | Agent 从理论到实践：问题、失败模式与工程应对 | 连接 Agent 核心理论和真实项目实践，按 Model、Tools、Orchestration、Context、State、Artifact、Evaluation、Multi-Agent、Runtime 梳理落地时的常见问题和应对原则。 |
| [agent-runtime-philosophy.md](./agent-runtime-philosophy.md) | Agent Runtime 哲学：从 Agent 能力到运行时治理 | 从 A/B/C/D-lite 实践出发，讨论 Agent 产品化为什么需要状态持久化、上下文治理、工具权限、安全边界、trace、评估和人工介入等运行时能力。 |
| [agent-system-boundaries.md](./agent-system-boundaries.md) | Agent 系统开发边界：把不确定智能放进可治理的软件边界 | 总结生产级 Agent 与传统软件的根本差异，说明任务、状态、工具、权限、产物、评估、人工介入和运维边界为什么是 Agent 系统开发的核心难点。 |
| [agent-frameworks-and-services-landscape.md](./agent-frameworks-and-services-landscape.md) | Agent 框架与服务选型地图：现成能力如何服务 Runtime 实践 | 梳理 LangGraph、OpenAI Agents SDK、AutoGen、CrewAI、Dify、Coze、云厂商托管 Agent 服务、观测评估和 Guardrails 工具，服务于项目 E / Runtime 实践选型。 |
| [multimodal-agent-capabilities-landscape.md](./multimodal-agent-capabilities-landscape.md) | 多模态 Agent 能力地图：从听、说、看、生成到运行时治理 | 分析语音、视觉、图像/视频生成、实时多模态、小模型生态对 Agent Runtime 的影响，提出项目 E 的多模态扩展实验路线。 |
| [agent-caching-strategies.md](./agent-caching-strategies.md) | 生产级 Agent 缓存策略：从精确命中到语义缓存 | 讨论 Agent 缓存从本地 JSON 到 Redis、TTL、限流、缓存穿透、语义缓存的演进路线，重点关注成本控制、稳定性和生产级并发。 |
| [model-runtime-and-engineering.md](./model-runtime-and-engineering.md) | LLM 运行时与工程化深度解析 | 解释模型加载、显存/内存管理、KV Cache、量化、推理加速和推理引擎选型，帮助理解本地模型和生产推理服务的工程约束。 |
| [reranker-deep-dive.md](./reranker-deep-dive.md) | RAG 检索加固：深度架构、模型与选型平衡报告 | 围绕项目 A 的 RAG 语义混淆问题，分析 Bi-Encoder、Cross-Encoder、Reranker、召回率瓶颈和检索链路调优策略。 |

## 建议阅读顺序

如果目标是系统理解 Agent 开发方法，建议按下面顺序阅读：

1. [agent-architectures-react-plan-reflect.md](./agent-architectures-react-plan-reflect.md)
2. [agent-design-methodology.md](./agent-design-methodology.md)
3. [agent-core-structure.md](./agent-core-structure.md)
4. [agent-reading-roadmap.md](./agent-reading-roadmap.md)
5. [agent-development-capability-and-interview.md](./agent-development-capability-and-interview.md)
6. [agent-context-engineering.md](./agent-context-engineering.md)
7. [agent-theory-to-practice.md](./agent-theory-to-practice.md)
8. [agent-runtime-philosophy.md](./agent-runtime-philosophy.md)
9. [agent-system-boundaries.md](./agent-system-boundaries.md)
10. [agent-frameworks-and-services-landscape.md](./agent-frameworks-and-services-landscape.md)
11. [multimodal-agent-capabilities-landscape.md](./multimodal-agent-capabilities-landscape.md)

如果目标是补充具体工程能力，可以按专题阅读：

| 关注点 | 推荐文档 |
|--------|----------|
| RAG 检索质量 | [reranker-deep-dive.md](./reranker-deep-dive.md) |
| 模型部署和推理性能 | [model-runtime-and-engineering.md](./model-runtime-and-engineering.md) |
| 成本、延迟和缓存 | [agent-caching-strategies.md](./agent-caching-strategies.md) |
| Agent 系统核心结构 | [agent-core-structure.md](./agent-core-structure.md) |
| Agent 经典文章、论文和工程文档阅读路线 | [agent-reading-roadmap.md](./agent-reading-roadmap.md) |
| Agent 开发能力和面试定位 | [agent-development-capability-and-interview.md](./agent-development-capability-and-interview.md) |
| Agent 上下文工程 | [agent-context-engineering.md](./agent-context-engineering.md) |
| Agent 从理论到实践 | [agent-theory-to-practice.md](./agent-theory-to-practice.md) |
| Agent Runtime / 项目 E 定位 | [agent-core-structure.md](./agent-core-structure.md)、[agent-theory-to-practice.md](./agent-theory-to-practice.md)、[agent-runtime-philosophy.md](./agent-runtime-philosophy.md)、[agent-system-boundaries.md](./agent-system-boundaries.md)、[agent-frameworks-and-services-landscape.md](./agent-frameworks-and-services-landscape.md) |
| 多模态与小模型能力 | [multimodal-agent-capabilities-landscape.md](./multimodal-agent-capabilities-landscape.md) |

## 维护约定

- 新增概念文档时，应在本文的“文档列表”中补充标题和内容简述。
- 如果文档用于支撑某个实践项目，应在简述中说明对应项目或实践背景。
- 对外部框架、模型、服务的介绍应尽量注明更新时间，并在正文中保留参考资料。
- 本目录优先保存方法论、架构判断和选型研究；具体项目操作记录应放在对应实践项目目录中。
