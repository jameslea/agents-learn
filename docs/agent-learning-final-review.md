# Agent 学习与实践阶段综述

> 更新时间：2026-05-19
>
> 本文用于对当前 `agents-learn` 项目的阶段性探索做一次总综述。它不是最终结论，也不是新的开发计划，而是把已经完成、部分完成和文档研究中的 Agent 实践放到同一张地图里，帮助后续继续讨论 Agent 类型、范式、上下文、记忆、工具、评估和 Runtime 的关系。

## 目录

- [1. 当前阶段判断](#1-当前阶段判断)
- [2. 全项目经验映射](#2-全项目经验映射)
  - 2.1 早期 01-15 阶段与架构深潜
  - 2.2 practice-projects A-E 深化实践
- [3. 关键项目对应的 Agent 类型](#3-关键项目对应的-agent-类型)
  - 3.1 A：RAG / Self-RAG Agent
  - 3.2 B：多角色内容协作 Agent
  - 3.3 C：自主调研与长任务 Agent
  - 3.4 D-lite：代码执行与自愈 Agent
  - 3.5 E：Runtime 与治理型 Agent 系统
- [4. 覆盖到的主要 Agent 范式](#4-覆盖到的主要-agent-范式)
- [5. 实践完成度分层](#5-实践完成度分层)
  - 5.1 较完整实践
  - 5.2 实践深入但结果不稳定
  - 5.3 文档研究与方法论沉淀
  - 5.4 基础和范式探索
- [6. 下一步讨论方向](#6-下一步讨论方向)

## 1. 当前阶段判断

当前项目已经做了足够多的尝试，覆盖了大部分常见 Agent 类型和范式：

- 工具调用、Prompt、Memory 等核心原子组件。
- ReAct、LangGraph、状态机和多 Agent supervisor。
- Self-RAG 与生产级闭环。
- smolagents、CrewAI、AutoGen、MetaGPT 等框架范式。
- LlamaIndex、Agentic RAG、企业知识库。
- BabyAGI 自主循环、Voyager 风格技能库。
- 低代码平台 Dify / Coze。
- RAGAS、Langfuse、Guardrails 等生产工程能力。
- RAG / Self-RAG。
- 多角色内容协作。
- 自主调研与长任务循环。
- 代码执行与最小自愈。
- 评估、安全和观测基础设施。
- Agent Runtime 与治理底座。
- 多模态、小模型、框架和云服务的文档研究。

这些实践的完成度并不相同：有些已经有可运行代码和测试，有些只做了最小闭环，有些主要停留在文档和方法论层面。但整体看，已经足以支撑一次更高层的总结：我们不是只学习了某个框架，而是在不断触碰 Agent 系统开发的核心问题。

当前最重要的阶段性认知是：

```text
Agent 系统不是单一技术点，
而是模型能力、上下文、记忆、工具、工作流、评估、安全、运行时和工程治理的组合。
```

## 2. 全项目经验映射

当前实践可以分为两条线：

- 早期 01-15 阶段：系统学习 Agent 原子组件、主流框架、高级范式和生产工程。
- practice-projects A-E：围绕真实坑位做更聚焦的实践、复盘和 Runtime 探索。

### 2.1 早期 01-15 阶段与架构深潜

| 项目 / 主题 | Agent 类型 | 主要范式 | 完成度 | 核心收获 |
|-------------|------------|----------|--------|----------|
| 01-core-concepts | Tool / Prompt / Memory 基础组件 | 工具调用、Prompt 模板、短期/长期记忆 | 基础实践 | Agent 不是单个模型调用，而是工具、提示、记忆和控制逻辑的组合 |
| 02-research-agent | Research Assistant | 搜索、整理、摘要、引用 | 基础实践 | 研究型 Agent 的价值来自检索、信息筛选和结构化总结，而不只是生成文本 |
| 03-langgraph-agent | Graph / State Machine Agent | LangGraph、ReAct、状态流转 | 较完整 | 显式状态机能降低 Agent 控制流的不确定性，是复杂任务的重要基础 |
| 04-multi-agent | Supervisor Multi-Agent | Supervisor、Worker、角色路由 | 基础实践 | 多 Agent 需要主管、路由和终止条件，否则容易变成无边界对话 |
| 05-final-project | Self-RAG / 生产级闭环 Agent | Self-RAG、检索评估、查询改写、自检索 | 较完整 | 生产级 RAG 需要检索、评估、改写、兜底和生成形成闭环 |
| 06-smolagents-intro | Code-as-action Agent | smolagents、代码式工具调用 | 浅尝 / 框架实验 | 代码即动作的范式很简洁，但更需要执行边界和安全约束 |
| 07-crewai-intro | Role-based Multi-Agent | CrewAI、角色、任务、Backstory | 浅尝 / 框架实验 | 角色描述能帮助组织任务，但不能替代流程、产物和评估 |
| 08-autogen-intro | Conversational Multi-Agent | AutoGen、对话协作、错误修正 | 浅尝 / 框架实验 | 对话式协作适合探索和自愈，但需要限制轮次和明确停止条件 |
| 09-execution-depth | Execution Safety / Code Agent | AST、subprocess、执行深度 | 机制研究 | 代码执行不是普通工具调用，必须区分静态分析、解释执行和系统副作用 |
| 10-llamaindex-agent | Agentic RAG / Data Agent | LlamaIndex、索引、查询引擎、数据中心 | 较完整 | 数据中心型 Agent 的核心是数据组织、索引质量和查询链路，而不只是聊天接口 |
| 11-metagpt-sop | SOP-driven Multi-Agent | MetaGPT、软件工程 SOP、角色流水线 | 框架实验 | SOP 能约束多 Agent 产出，但环境和依赖复杂度较高 |
| 12-autonomous-agents | Autonomous Task Agent | BabyAGI、任务生成、任务队列、优先级 | 框架实验 | 自主循环的关键是任务队列、优先级、停止条件和目标漂移控制 |
| 13-skill-library-agent | Skill Library Agent | Voyager 风格、技能沉淀、经验复用 | 框架实验 | Agent 的长期改进可以表现为技能库积累，而不只是记忆文本增加 |
| 14-lowcode-agent-platforms | Low-code Workflow Agent | Dify、Coze、可视化编排 | 文档研究 + 平台对比 | 低代码平台降低门槛，但复杂治理、版本和定制能力仍需谨慎评估 |
| 15-production-agent-engineering | Production Agent Engineering | RAGAS、Langfuse、Guardrails、评估观测 | 较完整 / 工程专题 | 生产级 Agent 需要评估、追踪、安全护栏、成本和回归体系 |
| architecture-deep-dives / chapter1-model-internals | Model-aware Agent Engineering | SFT / DPO、Prompt Caching、推理量化、硬件选型 | 文档研究 + 本地实践 | Agent 质量和成本受模型底层机制影响，不能只把 LLM 当黑盒 API |
| architecture-deep-dives / chapter2-data-engineering | Agentic RAG / Data Engineering | Rerank、HyDE、PDF ETL、GraphRAG、知识图谱 | 文档研究 + 较完整实践 | 数据摄入、检索策略和图谱结构决定知识型 Agent 的能力上限 |
| architecture-deep-dives / chapter3-distributed-system | Long-running Agent Infrastructure | Checkpoint、Actor Model、消息队列、多 Agent 协调 | 文档研究 | 长任务 Agent 需要断点续传、异步解耦、副作用控制和确定性边界 |
| architecture-deep-dives / chapter4-evaluation-security | Evaluation & Security Layer | LLM Judge、Guardrails、Prompt Injection、防御分层 | 文档研究 | 评估和安全不是上线前补丁，而是 Agent Runtime 的基础能力 |

`architecture-deep-dives` 可以看作从“会写 Agent”转向“理解 Agent 为什么会失控、变慢、变贵、不稳定”的工程深潜。它内部不是单个项目，而是四类底层能力的拆解：

| 子方向 | 包含内容 | 对 Agent 实践的意义 |
|--------|----------|---------------------|
| 模型底层与定向优化 | SFT vs DPO、Prompt Caching、推理量化、Mac / Linux 硬件差异、本地微调实验 | 帮助理解模型格式遵循、偏好对齐、上下文成本、推理吞吐和本地部署限制 |
| 深度数据工程 | Rerank、Query Expansion / HyDE、PDF 表格 ETL、GraphRAG、LightRAG 实测、向量检索与图谱检索对比 | 把 RAG 从“向量库调用”推进到可度量、可选择、可解释的数据摄入和检索策略 |
| 分布式 Agent 系统 | Checkpoint、Actor Model、消息队列、LangGraph / Temporal 式断点续传、多 Agent 协调模式 | 解释长任务、异步任务、失败恢复和多 Agent 协作为什么需要系统架构支撑 |
| 评估与安全防御 | LLM-as-a-Judge、工具成功率、忠实度、Prompt Injection、最小权限、Guardrails | 把质量、安全和权限治理提升为 Agent 系统的内建能力，而不是事后人工检查 |

### 2.2 practice-projects A-E 深化实践

| 项目 / 主题 | Agent 类型 | 主要范式 | 完成度 | 核心收获 |
|-------------|------------|----------|--------|----------|
| A：知识库问答 | RAG Agent / Retrieval Agent | 检索增强、Self-RAG、Rerank | 较完整 | RAG 的难点不只是向量检索，而是检索质量、证据忠实度、引用边界和失败兜底 |
| B：内容创作团队 | Multi-Agent / Content Workflow Agent | 多角色协作、SOP、Reviewer | 中等，实践深入但效果不稳定 | 多角色不自动产生高质量；必须有结构化产物、质量基线、事实核查和评审标准 |
| C：自主调研助手 | Autonomous Research Agent / Long-running Agent | 任务队列、计划执行、反思、报告生成 | 较完整 | 长任务需要任务拆解、状态管理、停止条件、成本控制和最终报告结构 |
| D-lite：代码自愈 | Code Execution Agent / Self-healing Agent | 安全执行、错误分类、有限修复、验证闭环 | 较完整 | 自愈必须绑定测试、安全边界、最大尝试次数、blocked 终态和 trace |
| E：Runtime & Governance | Agent Runtime / Governance Layer | Adapter、RuntimeState、Artifact、ToolPolicy、Trace | MVP 完成 | Runtime 是公共运行环境，不是单个 Agent；执行、观测和评估必须区分 |
| 00-evaluation-infra | Evaluation / Guardrails Infra | LLM Judge、metrics、guardrails | 浅尝 / 基础设施雏形 | 评估和护栏不能作为事后补丁，应逐步进入 Runtime 和任务流程 |
| 多模态能力研究 | Multimodal Agent Capability Mapping | ASR、TTS、VLM、小模型、Omni | 文档研究 | 多模态更像 Runtime 的感知与表达扩展，不应在无治理边界下直接进入高风险流程 |
| 框架与服务研究 | Agent Framework / Service Landscape | Dify、Coze、LangGraph、CrewAI、AutoGen、Manus、Claude Code | 文档研究 | 不同框架代表不同范式；选型应看任务控制流、状态、工具、部署和治理需求 |
| Agent Runtime 哲学与边界 | Agent Methodology / System Boundary | Runtime 八层模型、边界分析、可治理系统 | 文档研究 + 最小验证 | 生产级 Agent 的关键不是自主性最大化，而是把不确定智能放进可治理的软件边界 |

## 3. 关键项目对应的 Agent 类型

早期 01-15 阶段更像“范式覆盖”：通过不同框架和实验认识 Agent 可以如何被组织。practice-projects A-E 更像“问题深化”：围绕检索、协作、长任务、自愈和 Runtime 这些真实难点做更完整的实践。下面重点展开后者，因为它们暴露的问题更接近系统开发边界。

### 3.1 A：RAG / Self-RAG Agent

项目 A 代表的是数据中心型 Agent。它的核心不是让模型“知道更多”，而是让模型在回答时能够绑定检索证据。这个项目暴露了 RAG 系统最常见的问题：语义相似不等于答案可靠，向量召回不等于证据充分，模型能回答不等于回答被资料支撑。

它对应的 Agent 能力包括：

- 检索。
- 查询改写。
- Rerank。
- 引用生成。
- 检索失败识别。
- Self-RAG 式兜底和重试。

这个项目让我们看到：RAG Agent 的核心边界是“答案是否忠实于证据”，而不是“模型是否能给出流畅回答”。

### 3.2 B：多角色内容协作 Agent

项目 B 代表的是多角色和工作流型 Agent。它尝试把内容生产拆成 PM、Researcher、Writer、Reviewer 等角色，但实践说明：角色拆分本身并不会自动提升质量。多个 Agent 串联后，错误可能在上下文中累积，责任边界也可能变得更模糊。

项目 B 的价值不只在最终效果，而在于暴露了多 Agent 协作的真实困难：

- 角色边界需要明确。
- 角色之间不能只靠自然语言交接。
- Researcher 的证据质量会影响 Writer。
- Reviewer 不能只给泛泛意见，需要结构化评分和可执行建议。
- 最终报告质量需要独立评估，而不是依赖角色自评。

这个项目让我们看到：多 Agent 更像一种组织方式，不是质量保证机制。真正稳定的部分是 workflow、artifact、rubric、review 和 evaluation。

### 3.3 C：自主调研与长任务 Agent

项目 C 代表的是自主任务循环型 Agent。它关注的是一个 Agent 如何从目标出发，拆解任务、执行子任务、反思进展并形成最终报告。这类 Agent 比 RAG 和固定工作流更接近“自主”，但也更容易出现目标漂移和成本失控。

它暴露的核心问题包括：

- 任务如何拆解。
- 子任务如何排队。
- 什么时候继续研究，什么时候停止。
- 反思是提高质量，还是制造更多循环。
- 中间结果如何沉淀，而不是只留在上下文中。
- 最终报告如何证明已经覆盖目标。

这个项目让我们看到：自主性越高，越需要状态、预算、停止条件和评估。否则“自主”很容易变成不可控循环。

### 3.4 D-lite：代码执行与自愈 Agent

D-lite 代表的是代码执行和最小自愈 Agent。它不再停留在生成文本，而是让 Agent 面对真实代码、真实错误和真实验证。这个项目也让风险迅速变得具体：Agent 可能修改代码、引入回归、执行危险操作，甚至用错误方式“修复”问题。

D-lite 的关键经验是：

- 自愈必须绑定客观验证。
- 错误分类比盲目修复更重要。
- 修复轮数必须有限。
- 危险代码必须 blocked。
- 成功不能由模型自称修好，而要由测试或验证证明。
- trace 必须记录每次尝试、失败原因和修复摘要。

这个项目让我们看到：代码执行型 Agent 的核心不是“会写代码”，而是“能在安全边界内、基于验证信号做有限修复”。

### 3.5 E：Runtime 与治理型 Agent 系统

项目 E 最初被设想为评估和安全防线，后来重新定位为 Agent Runtime & Governance Lab。这个转向很重要：它说明很多能力不属于某个具体 Agent，而属于 Agent 系统的公共运行环境。

当前 Runtime MVP 已经覆盖：

- TaskContract。
- AgentAdapter。
- RuntimeState / StepExecution。
- Artifact / ArtifactStore。
- ToolPolicy / GovernedToolRunner。
- Trace / Replay。
- EvaluationResult。
- Human-in-the-loop。
- RunLock / run_id。
- Run manifest。

项目 E 的核心意义不是形成最终框架，而是帮助我们分清：

```text
Agent 业务逻辑负责解决具体任务；
Agent Runtime 负责提供执行、状态、工具、产物、trace、安全和恢复的公共支撑。
```

## 4. 覆盖到的主要 Agent 范式

当前项目已经覆盖或触及了多种 Agent 范式：

| 范式 | 项目体现 | 当前理解 |
|------|----------|----------|
| RAG / Self-RAG | 项目 A | 检索不是附加功能，而是证据约束机制 |
| Workflow Agent | 项目 B、B-runtime-lite | 稳定性来自流程、产物和评审，而不是角色名 |
| Multi-Agent | 项目 B | 多角色需要交接协议和责任边界，否则容易退化为 prompt 串联 |
| Autonomous Loop | 项目 C | 自主循环必须有任务队列、预算、停止条件和反思边界 |
| ReAct / Tool-use | 多个项目 | 工具调用必须受策略控制，不能只是函数列表 |
| Code Execution Agent | 项目 D-lite | 执行型 Agent 必须把安全和验证放在核心位置 |
| Self-healing Agent | 项目 D-lite | 自愈是“诊断-修复-验证”的有限闭环，不是无限自动改代码 |
| Runtime-governed Agent | 项目 E | Runtime 提供跨 Agent 的公共治理和运行能力 |
| Multimodal-capable Agent | 多模态研究 | 多模态是感知和表达通道扩展，需要 Runtime 管理输入、输出、成本和安全 |
| General Autonomous Agent | Manus / Claude Code 等研究 | 通用自主很强，但生产落地仍依赖工具、上下文、权限、trace 和人工边界 |

## 5. 实践完成度分层

为了避免把所有内容混为一谈，可以把当前成果分成三层。

### 5.1 较完整实践

- 03-langgraph-agent：LangGraph 状态机和 ReAct。
- 05-final-project：Self-RAG 生产级闭环。
- 10-llamaindex-agent：Agentic RAG / 数据中心型 Agent。
- 15-production-agent-engineering：评估、观测和 Guardrails。
- 项目 A：RAG / 知识库问答。
- 项目 C：自主调研助手。
- 项目 D-lite：代码执行安全与自愈。
- 项目 E：Agent Runtime & Governance MVP。

这些项目有较明确的代码、运行路径、产物和阶段性结论。

### 5.2 实践深入但结果不稳定

- 04-multi-agent：Supervisor 多 Agent。
- 07-crewai-intro：CrewAI 角色协作。
- 08-autogen-intro：AutoGen 对话协作。
- 11-metagpt-sop：MetaGPT SOP 多 Agent。
- 项目 B：内容创作团队。

项目 B 虽然效果不理想，但价值很高。它让我们看到多 Agent 协作不是简单拆角色，而是需要产物协议、事实核查、质量基线、上下文治理和评审闭环。

### 5.3 文档研究与方法论沉淀

- 09-execution-depth：代码执行机制和安全边界。
- 14-lowcode-agent-platforms：低代码平台对比。
- architecture-deep-dives / chapter1：模型底层、Prompt Caching、微调和推理优化。
- architecture-deep-dives / chapter2：Rerank、HyDE、PDF ETL、GraphRAG 和知识图谱检索。
- architecture-deep-dives / chapter3：Checkpoint、Actor Model、消息队列和长任务运行基础设施。
- architecture-deep-dives / chapter4：LLM Judge、Guardrails、Prompt Injection 和安全边界。
- Agent 设计方法论。
- Agent Runtime 哲学。
- Agent 框架与服务选型。
- 多模态能力地图。
- Agent 系统开发边界。
- 小模型与多模态趋势。

这些内容暂时不是完整工程实现，但为后续实践提供了判断框架。

### 5.4 基础和范式探索

- 01-core-concepts：工具、Prompt 和 Memory。
- 02-research-agent：基础研究助手。
- 06-smolagents-intro：代码式工具调用。
- 12-autonomous-agents：BabyAGI 自主任务循环。
- 13-skill-library-agent：Voyager 风格技能库。

这些内容有些较轻，但覆盖了 Agent 系统中的关键原型能力：工具调用、记忆、研究、任务循环、技能沉淀和框架对照。

## 6. 下一步讨论方向

这篇综述先完成第一步：项目经验映射。后续还需要继续讨论几个更核心的问题：

1. Agent 类型如何分类：按任务、按控制流、按工具能力，还是按自主性？
2. Agent 范式哪些是基础范式，哪些只是工程包装？
3. 上下文、状态、记忆、artifact 的边界到底怎么划？
4. 记忆管理应如何区分短期记忆、长期记忆、用户记忆、任务记忆和经验库？
5. Agent 的自主性如何分级，而不是笼统说 autonomous agent？
6. 多 Agent 是必要架构，还是很多时候只是 prompt 拆分？
7. Runtime 应该管理哪些公共能力，哪些仍应留在具体 Agent 项目中？

这些问题将决定后续是否需要形成新的文档：

```text
docs/concepts/agent-system-core-concepts.md
```

也可以继续扩展本文，把它发展成完整的 Agent 学习阶段总复盘。
