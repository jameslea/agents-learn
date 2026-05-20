# Agent 深度学习阅读路线：经典文章、公开论文与工程文档

> 更新时间：2026-05-20
>
> 本文用于保存 Agent 方向后续扩大学习范围的阅读路线。当前项目已经完成了多轮实践、总结和 Runtime Core 探索，但这些实践更多建立了直观认识和工程经验；如果要继续加深理解，需要把项目经验放回更大的研究和工程背景中阅读。本文不是论文综述，也不是排行榜，而是一份面向后续学习和实践的“阅读地图”。

## 资料汇总

说明：`关注主题` 表示这份资料主要帮助理解 Agent 系统中的哪类问题；`资料形态` 表示它是论文、工程文档、官方指南、白皮书还是思想文章；`重要程度` 表示当前项目后续学习时的优先级。

| 资料 | 关注主题 | 重要程度 | 资料形态 | 中文简述 |
|------|------|----------|------|----------|
| [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | 工程总论 | 必读 | 工程文章 | 区分 workflow 和 agent，总结 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer 等实用模式。 |
| [OpenAI: A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) | 工程总论 | 必读 | 官方指南 | 从工程落地角度解释 agent、tool、handoff、guardrail、human review、trace 等核心构件。 |
| [Kaggle / Google: Agents Whitepaper](https://www.kaggle.com/whitepaper-agents) | 核心架构 | 建议读 | 白皮书 | 用 Model、Tools、Orchestration 解释 Agent 一阶结构，适合建立总体架构坐标。 |
| [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | 推理与行动 | 必读 | 论文 | 提出 Thought / Action / Observation 循环，是 LLM Agent 推理与行动结合的基础范式。 |
| [Google Research Blog: ReAct](https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/) | 推理与行动 | 建议读 | 研究博客 | 用更易读的方式介绍 ReAct 背景、方法和实验结果。 |
| [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) | 工具使用 | 必读 | 论文 | 讨论模型如何学习在合适时机调用工具，适合理解工具使用能力。 |
| [Tree of Thoughts](https://arxiv.org/abs/2305.10601) | 规划与搜索 | 建议读 | 论文 | 将多个候选推理路径作为搜索对象，适合理解复杂任务中的搜索、打分和回溯。 |
| [Reflexion](https://arxiv.org/abs/2303.11366) | 反思与失败学习 | 必读 | 论文 | 用语言反馈和反思记忆改进后续尝试，适合理解失败经验如何沉淀。 |
| [Generative Agents](https://arxiv.org/abs/2304.03442) | 记忆系统 | 必读 | 论文 | 通过事件记忆、检索和反思生成可信行为，是 Agent 记忆系统的重要参考。 |
| [Voyager](https://arxiv.org/abs/2305.16291) | 技能库与长期任务 | 必读 | 论文 | 在开放环境中持续探索并沉淀代码技能，适合理解技能库和长期自主任务。 |
| [Voyager Project Page](https://voyager.minedojo.org/) | 技能库与长期任务 | 建议读 | 项目页 | 提供 Voyager 的项目说明、示例和补充材料。 |
| [AutoGen](https://arxiv.org/abs/2308.08155) | 多 Agent | 建议读 | 论文 | 通过多 Agent 对话组织复杂应用，适合理解多 Agent 协作的能力和风险。 |
| [Microsoft Research: AutoGen](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/) | 多 Agent | 可选读 | 研究页面 | AutoGen 官方研究介绍，便于了解框架背景。 |
| [SWE-agent](https://arxiv.org/abs/2405.15793) | 软件工程 Agent | 必读 | 论文 | 提出 Agent-Computer Interface 视角，说明代码 Agent 能力强依赖环境接口设计。 |
| [A Survey on LLM-based Autonomous Agents](https://arxiv.org/abs/2308.11432) | 自主 Agent 综述 | 进阶读 | 综述 | 系统梳理自主 Agent 的构成、应用和挑战，适合作为宏观补充阅读。 |
| [Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416) | 评估体系 | 进阶读 | 综述 | 梳理 Agent 评估对象、基准、方法和挑战，适合理解评估体系。 |
| [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 上下文工程 | 必读 | 论文 | 说明长上下文中间信息容易被忽略，支持 Context Builder 的必要性。 |
| [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 状态与恢复 | 必读 | 工程文档 | 介绍 checkpoint、thread、resume 等持久化能力，是可恢复 Agent 的重要工程参考。 |
| [LangChain / Deep Agents Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory) | 记忆系统 | 建议读 | 工程文档 | 说明长期记忆如何保存、读取和使用，适合对照 MemoryStore 设计。 |
| [LangChain Memory Overview](https://docs.langchain.com/oss/python/concepts/memory) | 记忆系统 | 建议读 | 工程文档 | 解释短期记忆和长期记忆的区别，适合补充记忆概念边界。 |
| [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/) | Trace 与观测 | 必读 | 工程文档 | 介绍 Agent run 中的 LLM、tool、handoff、guardrail 和自定义 trace 事件。 |
| [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/) | 安全与护栏 | 必读 | 工程文档 | 介绍输入、输出和工具调用前后的安全检查与阻断机制。 |
| [Langfuse Documentation](https://langfuse.com/docs/) | Trace 与观测 | 建议读 | 工程文档 | 介绍 LLM observability、trace、prompt、dataset 和 eval 等观测能力。 |
| [LangSmith Documentation](https://docs.smith.langchain.com/) | Trace 与评估 | 建议读 | 工程文档 | LangChain 生态的 observability、trace、dataset 和 evaluation 平台文档。 |
| [Arize Phoenix Documentation](https://arize.com/docs/phoenix) | Trace 与评估 | 建议读 | 工程文档 | 开源 AI observability 和 evaluation 工具，适合理解 trace、span、dataset 和实验分析。 |
| [AgentOps Documentation](https://docs.agentops.ai/v2/usage/tracking-agents) | Agent 观测工具 | 进阶读 | 工程文档 | 面向 AI agents 的观测和调试平台，强调 agent、tool、session、cost 和 replay。 |
| [AgentTrace: Structured Logging Framework](https://arxiv.org/abs/2602.10133) | Trace 与复盘 | 进阶读 | 论文 | 从 operational、cognitive、contextual 三个层面记录 Agent 运行轨迹，适合补充 trace 设计。 |
| [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/index) | 工具协议 | 建议读 | 协议文档 | 介绍模型与外部工具、资源、服务连接的协议化思路。 |
| [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html) | 底层思想 | 建议读 | 思想文章 | 讨论长期看通用计算和学习方法的重要性，适合校正过度手写规则的倾向。 |
| [Software 2.0](https://karpathy.github.io/2017/11/11/software2/) | 底层思想 | 建议读 | 思想文章 | 讨论从手写逻辑到模型逻辑的软件形态变化，适合理解 Agent 与传统软件的差异。 |
| [BDI Agent Architecture](https://learn.microsoft.com/en-us/archive/msdn-magazine/2019/january/machine-learning-leveraging-the-beliefs-desires-intentions-agent-architecture) | 传统智能体理论 | 可选读 | 经典智能体架构介绍 | 用 Belief、Desire、Intention 解释传统智能体结构，可作为现代 Agent 的概念参照。 |

## 目录

- [资料汇总](#资料汇总)
- [一、为什么需要扩大学习范围](#一为什么需要扩大学习范围)
- [二、阅读路线总览](#二阅读路线总览)
- [三、第一组：Agent 工程总论和实践方法](#三第一组agent-工程总论和实践方法)
- [四、第二组：Reasoning + Acting 的基础范式](#四第二组reasoning--acting-的基础范式)
- [五、第三组：规划、反思和搜索](#五第三组规划反思和搜索)
- [六、第四组：记忆、技能库和长期任务](#六第四组记忆技能库和长期任务)
- [七、第五组：多 Agent 与软件工程 Agent](#七第五组多-agent-与软件工程-agent)
- [八、第六组：Context、State、Checkpoint 与 Runtime](#八第六组contextstatecheckpoint-与-runtime)
- [九、第七组：Trace、观测、评估与安全治理](#九第七组trace观测评估与安全治理)
- [十、第八组：更底层的思想来源](#十第八组更底层的思想来源)
- [十一、和当前项目的对应关系](#十一和当前项目的对应关系)
- [十二、推荐阅读顺序](#十二推荐阅读顺序)
- [十三、阅读笔记模板](#十三阅读笔记模板)
- [十四、阶段性判断](#十四阶段性判断)
- [参考资料](#参考资料)

## 一、为什么需要扩大学习范围

当前项目已经覆盖了很多 Agent 类型和范式：

- RAG / Agentic RAG。
- Research Agent。
- LangGraph 状态机 Agent。
- CrewAI / AutoGen 多 Agent。
- MetaGPT SOP。
- 自主循环 Agent。
- Skill Library Agent。
- Low-code Agent 平台。
- D-lite 自愈执行 Agent。
- Runtime Core。
- Code Review Mini 场景。

这些实践的价值很大，因为它们让很多抽象问题变得具体：上下文会污染，记忆会过期，工具调用会失败，状态恢复很麻烦，trace 太少无法复盘，trace 太多又无法阅读，多 Agent 很容易变成自由文本互相聊天，Runtime Core 做不好会增加复杂度。

但仅靠项目实践也有局限：

```text
实践项目容易陷入局部细节；
论文和白皮书容易停留在抽象理论；
真正有价值的学习，是把两者放在一起互相校正。
```

因此，后续阅读不应只是“看更多论文”，而是围绕当前已经暴露出来的核心问题去读：

| 当前问题 | 需要补充的外部视角 |
|----------|--------------------|
| Agent 到底是什么 | 工程总论、Agent 架构共识、传统智能体理论 |
| 如何组织行动 | [ReAct](https://arxiv.org/abs/2210.03629)、[Toolformer](https://arxiv.org/abs/2302.04761)、计划与搜索、状态机 |
| 如何避免失控 | Guardrails、工具权限、人类介入、安全边界 |
| 如何长期运行 | Memory、Checkpoint、Resume、Durable Execution |
| 如何沉淀能力 | Skill Library、经验记忆、可复用工具、Artifact |
| 如何复盘和改进 | Trace、Observability、Evaluation、Regression Set |
| 如何工程落地 | Runtime、接口、Schema、部署、版本治理 |

本文的目标是把这些阅读内容组织成一条路线：先建立核心判断，再进入关键机制，最后回到工程验证。

## 二、阅读路线总览

建议把 Agent 阅读分成八组。

| 组别 | 主题 | 主要解决的问题 |
|------|------|----------------|
| 1 | Agent 工程总论和实践方法 | 什么任务值得用 Agent，复杂度如何控制 |
| 2 | Reasoning + Acting 基础范式 | Agent 如何边推理、边行动、边观察 |
| 3 | 规划、反思和搜索 | Agent 如何处理多步任务、失败重试和候选路径 |
| 4 | 记忆、技能库和长期任务 | Agent 如何跨步骤、跨任务积累经验 |
| 5 | 多 Agent 与软件工程 Agent | 多角色协作、代码 Agent、Agent-Computer Interface |
| 6 | Context、State、Checkpoint 与 Runtime | 长任务如何上下文治理、状态保存和恢复 |
| 7 | Trace、观测、评估与安全治理 | 如何知道 Agent 为什么成功或失败 |
| 8 | 更底层的思想来源 | 为什么“手写规则”与“学习系统”之间存在张力 |

这里有一个重要阅读原则：

```text
不要按论文发表时间线阅读，
而要按 Agent 系统能力阅读。
```

例如，阅读 [ReAct](https://arxiv.org/abs/2210.03629) 时，不只看它提出了 Thought / Action / Observation，而要思考：

- 当前 Runtime Core 的 Step 是否能表达这个循环？
- Tool Call 是否有权限和错误处理？
- Observation 是否进入 Trace？
- Observation 是否会污染后续 Context？
- 失败重试是否进入 blocked，而不是无限循环？

这样阅读才会和当前项目形成互相支撑。

## 三、第一组：Agent 工程总论和实践方法

这组资料适合先读，因为它们不是具体算法论文，而是回答“什么时候用 Agent、怎么控制复杂度、应该优先构造什么能力”。

### 3.1 [Anthropic：Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

推荐级别：必读。

这篇文章的重要性在于，它明确区分了 workflow 和 agent：

- Workflow：路径相对固定，LLM 和工具按预先写好的控制流执行。
- Agent：模型可以根据环境反馈动态决定下一步行动。

这对当前项目很重要，因为很多场景并不需要一开始就做“完全自主 Agent”。更稳妥的路线是：

```text
先用 workflow 控制任务边界；
再把局部需要判断、选择、恢复的部分交给 Agent；
最后才考虑更强自主性。
```

它还总结了 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer 等模式。这些模式比“多角色命名”更关键，因为它们描述的是任务控制结构，而不是角色故事。

对当前项目的启发：

- Runtime Core 不应该默认追求全自主。
- Step、Tool、Artifact、Trace 比“Agent 名字”更重要。
- 复杂系统应从可控 workflow 开始，逐步引入自主决策点。

### 3.2 [OpenAI：A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)

推荐级别：必读。

这份指南的价值在于，它从工程落地角度讨论 agent、tool、handoff、guardrail、human review、trace 等能力。它和当前 Runtime Core 的方向非常接近：不是只讨论模型如何回答，而是讨论一个 Agent 应用如何被组织、约束和观测。

对当前项目的启发：

- Agent 应该有明确任务边界和停止条件。
- Tool 调用需要 schema、权限和错误处理。
- Handoff 不应只是自然语言转述，而应有结构化交接。
- Guardrails 和 Human Review 是工程能力，不是额外装饰。
- Trace 应覆盖 LLM、Tool、Handoff、Guardrail 和自定义事件。

### 3.3 [Google Agents Whitepaper](https://www.kaggle.com/whitepaper-agents) / Agent 总体架构材料

推荐级别：建议读。

这类资料通常会把 Agent 拆成：

```text
Model + Tools + Orchestration
```

这个抽象很适合作为 Agent 一阶结构。模型负责理解和决策，工具连接外部世界，编排层管理上下文、状态、行动循环和停止条件。

对当前项目的启发：

- Context / State / Memory / Artifact / Trace 都不是孤立概念，它们服务于 Orchestration。
- Runtime Core 的定位不是替代 Agent，而是给 Agent 提供公共运行环境。
- “工具接入”不是简单函数调用，而是模型和外部世界之间的受控接口。

### 3.4 为什么先读工程总论

如果直接从 [ReAct](https://arxiv.org/abs/2210.03629)、[Tree of Thoughts](https://arxiv.org/abs/2305.10601)、[Reflexion](https://arxiv.org/abs/2303.11366) 读起，很容易把 Agent 理解成 prompt 技巧。但当前项目已经证明，真正困难的部分往往不在单次 prompt，而在：

- 任务边界。
- 上下文选择。
- 状态持久化。
- 工具权限。
- 产物交接。
- 失败处理。
- 观测复盘。

因此，先读工程总论，有助于建立更稳的判断：Agent 不是“聪明 prompt”，而是一个可运行、可治理、可恢复的软件系统。

## 四、第二组：Reasoning + Acting 的基础范式

这一组回答 Agent 的基础行动循环：模型如何把推理和行动交错起来。

### 4.1 [ReAct：Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)

推荐级别：必读。

ReAct 是 LLM Agent 方向最核心的论文之一。它提出的核心并不是“让模型多想一想”，而是把推理、行动和观察组织成循环：

```text
Thought -> Action -> Observation -> Thought -> ...
```

这个循环把模型从一次性问答推进到可与环境交互的任务执行。它的价值在于：

- Reasoning 可以帮助模型维护计划、处理异常和更新目标。
- Acting 可以让模型通过工具或环境获得新信息。
- Observation 可以反过来修正下一步推理。

对当前项目的启发：

- Runtime Core 的 `Step` 应该能够表达一次行动单元。
- Tool Call 的返回不应只作为文本拼回 prompt，也应进入 Trace 和 Artifact。
- Observation 是否进入下一轮 Context，需要经过 Context Builder 选择，而不是自动全部注入。
- ReAct 循环必须有停止条件、重试预算和 blocked 状态。

实践阅读问题：

- D-lite 的自愈循环是否可以看作 ReAct 的一个工程化特例？
- Code Review Mini 的三步流程是否可以扩展成 ReAct 风格的工具观察循环？
- ReAct 的 Observation 在当前 Runtime Core 中应该属于 Trace、Artifact，还是 Context Source？

### 4.2 [Toolformer：Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)

推荐级别：必读。

Toolformer 关注模型如何学会在合适时机调用外部工具。它的重要性不在于当前项目要训练模型，而在于它强化了一个认识：

```text
工具调用不是附属功能，而是 Agent 能力结构的一部分。
```

一个 Agent 能否可靠工作，很大程度取决于工具接口是否设计清楚：

- 工具什么时候可用？
- 输入参数如何约束？
- 输出如何结构化？
- 错误如何返回？
- 工具调用的副作用是否受控？
- 工具结果如何进入上下文？

对当前项目的启发：

- Tool 需要 schema，不应只是任意函数。
- Tool Policy 是 Runtime Core 的核心能力。
- 工具返回应被记录为结构化 Trace Event。
- 工具结果是否进入 Memory，需要单独判断。

### 4.3 ReAct 和 Toolformer 的组合理解

ReAct 更像运行时行动循环：

```text
模型决定下一步要做什么。
```

Toolformer 更像工具使用能力：

```text
模型知道什么时候该调用什么工具。
```

工程实践中，两者需要被 Runtime 接住：

```text
模型提出行动意图
  -> Runtime 校验工具权限
  -> Tool 执行
  -> Runtime 记录结果
  -> Context Builder 选择是否反馈给模型
```

这也是当前 Runtime Core 应继续强化的方向。

## 五、第三组：规划、反思和搜索

这一组资料适合在理解 ReAct 后阅读。它们讨论 Agent 如何处理更长链路、更复杂决策和失败改进。

### 5.1 [Tree of Thoughts](https://arxiv.org/abs/2305.10601)

推荐级别：建议读。

Tree of Thoughts 的核心是：不要让模型只沿着一条推理路径往下走，而是生成多个中间候选，评估它们，再选择或回溯。

这对 Agent 的启发是：

- 对复杂任务，单一路径执行很脆弱。
- 可以把中间思路当作可评估对象。
- 搜索、打分、回溯可以作为编排策略，而不只是 prompt 技巧。

对当前项目的启发：

- Runtime Core 可以支持多个候选 Artifact。
- Evaluation 可以在中间步骤发生，而不是只评估最终产物。
- 失败不一定直接重试同一路径，也可以生成替代方案。

但也要注意：ToT 会显著增加成本和延迟，不适合所有任务。它更适合高价值、低频、需要探索的任务。

### 5.2 [Reflexion](https://arxiv.org/abs/2303.11366)

推荐级别：必读。

Reflexion 关注 Agent 如何通过语言反馈改进后续尝试。它不依赖模型参数更新，而是把失败经验、反馈和反思写入可被后续使用的记忆中。

对当前项目的启发非常直接：

- 失败不是只记录 error message，还应转化为可复用经验。
- Memory 不应只保存事实，也可以保存“下次不要这样做”的经验。
- 反思内容不能无条件长期保存，需要置信度、作用域、过期和验证机制。
- Blocked 状态也可以产生一条经验：为什么停下，缺什么信息，下一步需要谁介入。

这与当前 Memory / State 分层关系密切：

| Reflexion 概念 | Runtime Core 对应能力 |
|----------------|-----------------------|
| feedback | Trace / Evaluation / Human Review |
| reflection | MemoryRecord 候选 |
| retry | Step Retry / Checkpoint Resume |
| failure signal | RuntimeState blocked / failed |

### 5.3 规划、反思和搜索的工程边界

这组论文容易让人产生一个误解：只要增加反思和搜索，Agent 就会变强。工程上要更谨慎：

- 搜索需要预算。
- 反思需要验证。
- 重试需要停止条件。
- 候选需要结构化产物。
- 失败需要进入 blocked，而不是无限循环。

因此，当前项目如果要吸收这组思想，优先不是实现复杂 ToT，而是实现：

```text
失败原因结构化 -> 反思候选 -> 记忆准入 -> 下次上下文选择
```

这比盲目增加多轮自我反思更有工程价值。

## 六、第四组：记忆、技能库和长期任务

这一组资料对应当前项目中最核心、也最容易复杂化的主题之一：Memory。

### 6.1 [Generative Agents](https://arxiv.org/abs/2304.03442)

推荐级别：必读。

Generative Agents 提出了一个非常有代表性的记忆架构：记录经验、检索相关记忆、定期综合反思，并用这些记忆影响计划和行为。

它对当前项目的启发是：

- 记忆不是聊天历史。
- 记忆需要写入、检索、反思和更新。
- 低层事件可以被综合成高层经验。
- 记忆检索需要考虑相关性、重要性和时间因素。

但它也提示了风险：

- 记忆越多，污染可能越严重。
- 反思生成的高层结论可能并不可靠。
- 如果没有作用域和过期机制，记忆会成为长期错误来源。

当前项目可以吸收的核心不是完整模拟社会行为，而是记忆机制：

```text
event -> memory candidate -> validation -> memory record -> retrieval -> context injection
```

### 6.2 [Voyager](https://arxiv.org/abs/2305.16291)

推荐级别：必读。

Voyager 是理解“技能库 Agent”的重要论文。它在 Minecraft 环境中持续探索，并把学到的行为保存为可复用代码技能。

它的核心组件包括：

- 自动课程，用于驱动探索。
- 技能库，用于保存和检索可执行行为。
- 迭代提示机制，用环境反馈、执行错误和自我验证改进代码。

对当前项目的启发：

- Memory 不只是事实记忆，也可以是 Skill Memory。
- 技能应是可执行、可检索、可组合的产物。
- 技能保存前需要验证，不能只因为模型说“有用”就进入库。
- Runtime 应记录技能产生、验证、失败和复用过程。

这和我们之前的 `13-skill-library-agent` 实践直接相关，也和后续 Runtime Core 的 Artifact / Memory 边界相关。

### 6.3 [Memory for Autonomous Agents](https://arxiv.org/abs/2308.11432) / Episodic Memory 相关综述

推荐级别：进阶读。

记忆系统可以按类型拆分：

| 记忆类型 | 中文理解 | 典型内容 |
|----------|----------|----------|
| Semantic Memory | 语义记忆 | 稳定事实、项目约定、用户偏好 |
| Episodic Memory | 情节记忆 | 某次任务发生了什么、为什么失败、如何恢复 |
| Procedural Memory | 程序性记忆 | 技能、操作步骤、SOP、工具使用方法 |
| Working Memory | 工作记忆 | 当前任务临时状态、当前 step 需要的信息 |

当前项目已经初步区分 project memory、task state、artifact。后续可以进一步补充：

- MemoryRecord 的 scope。
- MemoryRecord 的 confidence。
- MemoryRecord 的 source。
- MemoryRecord 的 expiry。
- MemoryRecord 的 validation status。
- MemoryRecord 和 ArtifactRecord 的引用关系。

这组阅读的重点不是追求复杂记忆系统，而是理解一个原则：

```text
长期记忆必须可验证、可过期、可追溯、可隔离。
```

## 七、第五组：多 Agent 与软件工程 Agent

这一组适合结合当前项目中 CrewAI、AutoGen、MetaGPT、D-lite、Code Review Mini 的实践阅读。

### 7.1 [AutoGen](https://arxiv.org/abs/2308.08155)

推荐级别：建议读。

AutoGen 代表了多 Agent conversation 的一条路线：多个 Agent 通过对话协作，可能包含工具、代码执行、人类介入和动态群聊。

它的价值在于展示多 Agent 的灵活性；它的风险也很明显：如果没有明确任务边界和交接格式，多 Agent 很容易退化为自由文本聊天。

对当前项目的启发：

- 多 Agent 的关键不是“角色多”，而是分工、工具、状态和交接。
- Agent 间通信需要结构化 Artifact。
- 人类介入不应只在最后审批，也可以出现在中间决策点。
- 多 Agent trace 必须能回答：谁在什么时候基于什么输入做了什么决定。

### 7.2 [SWE-agent](https://arxiv.org/abs/2405.15793)

推荐级别：必读。

SWE-agent 的重要性在于提出 Agent-Computer Interface 这个视角。它说明代码 Agent 的性能不仅取决于模型，还取决于 Agent 与计算机环境之间的接口设计。

对当前项目启发很大：

- 工具接口、命令反馈、文件浏览、测试执行，都是 Agent 能力的一部分。
- 好的接口可以降低模型负担。
- Agent 的环境应该被设计，而不是简单暴露整个 shell。
- Trace 应记录 Agent 如何浏览、修改、测试和判断。

这与 D-lite 和 Code Review Mini 都高度相关。当前项目中的工具权限、安全边界、trace、artifact，本质上都是在设计一个更受控的 Agent-Computer Interface。

### 7.3 多 Agent 阅读的重点

多 Agent 论文和框架很多，但当前阶段不建议陷入“角色越多越智能”的误区。更值得关注的是：

- 每个 Agent 的输入和输出是否结构化。
- 每个 Agent 是否拥有不同工具权限。
- Agent 之间是否通过 Artifact 交接。
- 是否存在统一 RuntimeState。
- 是否有全局停止条件。
- 是否能从 Trace 复盘多 Agent 协作失败点。

一个实用判断是：

```text
如果单 Agent + 明确 workflow 能解决，就不要过早多 Agent。
如果多 Agent 只是多个 LLM 互相聊天，通常不够工程化。
```

## 八、第六组：Context、State、Checkpoint 与 Runtime

这一组资料直接对应当前 Runtime Core 项目的核心。

### 8.1 [Lost in the Middle](https://arxiv.org/abs/2307.03172)

推荐级别：必读。

这篇论文提醒我们：长上下文窗口不等于模型能稳定利用所有上下文。模型对上下文不同位置的信息利用并不均匀，重要信息放在长上下文中间时可能被忽略。

对当前项目的启发：

- Context Builder 不能只是把更多信息塞进去。
- 上下文选择比上下文长度更重要。
- 关键信息应被显式摘要、排序和标注。
- 大文档应通过引用、检索、摘要和分段进入，而不是全量拼接。

这正好支持当前 `agent-context-engineering.md` 的核心判断：

```text
上下文是有限注意力资源。
```

### 8.2 [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) / Durable Execution

推荐级别：必读工程文档。

LangGraph 的 persistence 和 durable execution 文档非常值得读，因为它们把 Agent 长任务中最难的一类问题具体化了：

- checkpoint。
- resume。
- time travel debugging。
- human-in-the-loop。
- pending writes recovery。
- fault-tolerant execution。

对当前 Runtime Core 的启发：

- Checkpoint 不是日志，而是可恢复状态。
- Resume 需要知道从哪个 step、哪个状态、哪个输入继续。
- 人工介入依赖可暂停、可恢复的状态保存。
- Durable execution 是 Runtime 能力，不应散落在业务代码里。

当前项目第 3 阶段 `Checkpoint / Resume` 与这类文档高度对应。

### 8.3 [LangChain / Deep Agents Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory) 文档

推荐级别：建议读。

这类文档的价值在于区分短期记忆和长期记忆：

- 短期记忆通常属于线程、会话或当前任务 state。
- 长期记忆跨会话保存，需要独立 store。
- 有些 memory 是只读的，比如技能和组织策略。
- 有些 memory 可写，但需要控制写入时机和合并策略。

对当前项目的启发：

- `RuntimeState` 不等于 `MemoryStore`。
- `Artifact` 不等于长期记忆。
- Memory 写入应由策略触发，而不是所有内容自动保存。
- Memory 读取应按 scope、tag、confidence、freshness 选择。

### 8.4 [MCP：Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/basic/index)

推荐级别：建议读。

MCP 的价值在于提供工具和外部数据源连接的协议化思路。它不是 Agent Runtime 的全部，但它说明工具接入正在从“项目内临时函数”走向标准化。

对当前项目的启发：

- Tool 接口应有清晰协议。
- 外部资源应作为 Resource 暴露，而不是全部注入 prompt。
- 工具和数据源应该可发现、可描述、可授权、可审计。
- MCP 也提醒我们：工具协议越通用，安全边界越重要。

当前 Runtime Core 不需要马上实现 MCP，但可以吸收其思想：工具不是随便暴露给模型的函数，而是受协议和权限治理的外部接口。

## 九、第七组：Trace、观测、评估与安全治理

这一组对应 Agent 从 demo 走向可维护系统的关键能力。

### 9.1 [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/) / [Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/)

推荐级别：必读工程文档。

OpenAI Agents SDK 的 Tracing 文档强调，trace 应记录一次 agent run 中的多类事件：

- LLM generation。
- Tool call。
- Handoff。
- Guardrail。
- Custom event。

Guardrails 文档则强调输入、输出和工具调用前后的检查。

对当前项目的启发：

- Trace 不只是记录文本日志，而是结构化事件。
- Guardrail 应该能阻断执行，而不是只给提示。
- 高风险工具应在执行前进入审批或 blocked。
- Trace 与 Guardrail 应能关联：是哪条规则阻断了哪个动作。

### 9.2 [Langfuse](https://langfuse.com/docs/) / [LangSmith](https://docs.smith.langchain.com/) / [Phoenix](https://arize.com/docs/phoenix) 等观测工具

推荐级别：建议读文档并选择性试用。

当前项目 `.env` 已经配置 Langfuse，因此后续可以考虑把本地 trace 与 Langfuse 对接。但即使不立即接入，也值得理解这些工具解决的问题：

- LLM 调用记录。
- Token 和成本统计。
- Latency 统计。
- Prompt 版本管理。
- Trace 可视化。
- Dataset / Eval。
- Human annotation。

需要注意的是，观测工具通常能回答：

```text
发生了什么？
```

但不一定能自动回答：

```text
为什么失败？
下一步应该改什么？
```

因此，Runtime Core 仍然需要自己的结构化诊断能力，例如：

- step status。
- blocked reason。
- selected context source。
- memory decision reason。
- artifact validation result。
- tool policy decision。

### 9.3 [Agent Evaluation 综述](https://arxiv.org/abs/2503.16416)

推荐级别：进阶读。

Agent 评估比普通 LLM 输出评估复杂，因为它涉及过程、工具、状态和环境反馈。只看最终答案往往不够。

Agent 评估应至少考虑：

- 最终结果是否正确。
- 中间步骤是否合理。
- 工具调用是否必要且安全。
- 是否遵守预算和权限。
- 是否可复现。
- 失败是否可解释。
- 人工介入点是否合理。

对当前项目的启发：

- Evaluation 不应替代 Runtime。
- Evaluation 是 Runtime 之上的质量反馈层。
- Trace 是 Evaluation 的数据基础。
- 回归样本应来自真实失败案例。

## 十、第八组：更底层的思想来源

这一组不是 LLM Agent 论文，但有助于建立更深层的判断。

### 10.1 [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)

推荐级别：建议读。

Rich Sutton 的 The Bitter Lesson 提醒我们：长期看，利用计算规模和学习能力的方法往往超过大量手工编码的领域知识。

对 Agent 开发的启发是双面的：

一方面，不应幻想用大量手写规则完全替代模型能力。另一方面，也不应误解为“什么都交给模型”。Agent 工程里的规则、schema、guardrail、state、trace 并不是替代智能，而是给智能提供边界和运行环境。

更合理的理解是：

```text
模型负责不确定性推理；
软件工程负责边界、状态、接口、复盘和治理。
```

### 10.2 [Software 2.0](https://karpathy.github.io/2017/11/11/software2/)

推荐级别：建议读。

Software 2.0 讨论的是从手写逻辑转向由数据训练出的模型逻辑。Agent 系统可以看作 Software 2.0 / 3.0 继续向外扩展：不仅模型行为不完全由手写代码决定，运行过程也包含大量自然语言、工具调用、动态上下文和环境反馈。

对当前项目的启发：

- Agent 开发不是传统 CRUD 软件开发的简单变体。
- 不确定性、评估、数据、prompt、模型版本都成为软件系统的一部分。
- 工程边界比以往更重要，因为内部行为更不确定。

### 10.3 [BDI：Belief-Desire-Intention](https://learn.microsoft.com/en-us/archive/msdn-magazine/2019/january/machine-learning-leveraging-the-beliefs-desires-intentions-agent-architecture)

推荐级别：可选读。

BDI 是传统智能体理论中的经典结构：

- Belief：Agent 对世界的认识。
- Desire：Agent 想达成的目标。
- Intention：Agent 已承诺执行的计划或行动意图。

虽然现代 LLM Agent 不一定直接使用 BDI 架构，但这个框架仍然有启发：

| BDI 概念 | 现代 Agent 对应 |
|----------|----------------|
| Belief | Context / Memory / State 中的世界认识 |
| Desire | Task Goal / User Intent / Success Criteria |
| Intention | Selected Plan / Current Step / Tool Action |

它提醒我们：Agent 不只是生成文本，而是在目标、信念和行动之间做持续协调。

## 十一、和当前项目的对应关系

下面把推荐资料和当前项目已有实践关联起来，方便阅读时对照。

| 当前项目主题 | 推荐阅读 |
|--------------|----------|
| Agent 核心结构 | [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)；[OpenAI Agents Guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)；[Google Agents Whitepaper](https://www.kaggle.com/whitepaper-agents) |
| ReAct / 状态机 | [ReAct](https://arxiv.org/abs/2210.03629)；[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)；[Tree of Thoughts](https://arxiv.org/abs/2305.10601) |
| 工具调用和权限 | [Toolformer](https://arxiv.org/abs/2302.04761)；[OpenAI Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/)；[MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/index)；[SWE-agent](https://arxiv.org/abs/2405.15793) |
| 上下文工程 | [Lost in the Middle](https://arxiv.org/abs/2307.03172)；[LangChain / Deep Agents Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory)；[LangChain Memory Overview](https://docs.langchain.com/oss/python/concepts/memory) |
| 记忆系统 | [Generative Agents](https://arxiv.org/abs/2304.03442)；[Voyager](https://arxiv.org/abs/2305.16291)；[LLM-based Autonomous Agents Survey](https://arxiv.org/abs/2308.11432)；[LangChain Memory](https://docs.langchain.com/oss/python/concepts/memory) |
| 技能库 | [Voyager](https://arxiv.org/abs/2305.16291)；[SWE-agent](https://arxiv.org/abs/2405.15793)；当前 `13-skill-library-agent` |
| 多 Agent | [AutoGen](https://arxiv.org/abs/2308.08155)；[CrewAI 文档](https://docs.crewai.com/)；[MetaGPT](https://github.com/FoundationAgents/MetaGPT) / SOP 相关资料 |
| 代码 Agent | [SWE-agent](https://arxiv.org/abs/2405.15793)；D-lite；Code Review Mini |
| Runtime Core | [LangGraph Durable Execution / Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)；[OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)；[Langfuse 文档](https://langfuse.com/docs/) |
| Trace / 复盘 | [OpenAI Tracing](https://openai.github.io/openai-agents-python/tracing/)；[Langfuse](https://langfuse.com/docs/)；[AgentOps](https://docs.agentops.ai/v2/usage/tracking-agents)；[AgentTrace](https://arxiv.org/abs/2602.10133) |
| 评估体系 | [Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416)；[SWE-bench](https://www.swebench.com/) / [SWE-agent](https://arxiv.org/abs/2405.15793) |
| 方法论和边界 | [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)；[Software 2.0](https://karpathy.github.io/2017/11/11/software2/)；[BDI](https://learn.microsoft.com/en-us/archive/msdn-magazine/2019/january/machine-learning-leveraging-the-beliefs-desires-intentions-agent-architecture)；当前 [agent-system-boundaries.md](./agent-system-boundaries.md) |

当前项目最值得带着问题重读的部分是：

- [agent-core-structure.md](./agent-core-structure.md)
- [agent-context-engineering.md](./agent-context-engineering.md)
- [agent-theory-to-practice.md](./agent-theory-to-practice.md)
- [agent-runtime-philosophy.md](./agent-runtime-philosophy.md)
- [agent-system-boundaries.md](./agent-system-boundaries.md)
- [agent-frameworks-and-services-landscape.md](./agent-frameworks-and-services-landscape.md)
- [../../practice-projects/06-agent-runtime-core/docs/agent-non-functional-capabilities-overview.md](../../practice-projects/06-agent-runtime-core/docs/agent-non-functional-capabilities-overview.md)

## 十二、推荐阅读顺序

### 12.1 第一轮：建立整体框架

目标：知道 Agent 系统应该如何分层，不再被单个框架或 demo 带偏。

建议顺序：

1. [Anthropic：Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)。
2. [OpenAI：A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)。
3. [ReAct](https://arxiv.org/abs/2210.03629)。
4. [Toolformer](https://arxiv.org/abs/2302.04761)。
5. [SWE-agent](https://arxiv.org/abs/2405.15793)。

第一轮读完后，应能回答：

- Agent 和 workflow 的区别是什么？
- Agent 为什么需要工具？
- 工具为什么需要权限和 schema？
- ReAct 循环为什么必须有停止条件？
- 为什么 Agent-Computer Interface 会影响代码 Agent 能力？

### 12.2 第二轮：补齐长期任务能力

目标：理解记忆、反思、技能库和可恢复执行。

建议顺序：

1. [Generative Agents](https://arxiv.org/abs/2304.03442)。
2. [Reflexion](https://arxiv.org/abs/2303.11366)。
3. [Voyager](https://arxiv.org/abs/2305.16291)。
4. [LangGraph Persistence / Durable Execution](https://docs.langchain.com/oss/python/langgraph/persistence)。
5. [LangChain / Deep Agents Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory)。

第二轮读完后，应能回答：

- 记忆和上下文有什么区别？
- 记忆写入时机如何判断？
- 失败经验如何变成可用记忆？
- 技能库和普通 memory 有什么区别？
- Checkpoint 为什么不是普通日志？

### 12.3 第三轮：进入工程治理

目标：理解生产级 Agent 为什么需要 trace、guardrail、eval、human-in-the-loop。

建议顺序：

1. [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)。
2. [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/)。
3. [Langfuse 文档](https://langfuse.com/docs/)。
4. [Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416)。
5. [AgentOps](https://docs.agentops.ai/v2/usage/tracking-agents) / [AgentTrace](https://arxiv.org/abs/2602.10133) 相关资料。

第三轮读完后，应能回答：

- Trace 应该记录哪些事件？
- Trace 和日志有什么区别？
- Guardrail 应该在哪些位置生效？
- Eval 是否只评估最终答案？
- 如何从真实失败中形成回归样本？

### 12.4 第四轮：回到更底层的思想

目标：建立长期判断，不被短期框架热度影响。

建议顺序：

1. [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)。
2. [Software 2.0](https://karpathy.github.io/2017/11/11/software2/)。
3. [BDI Agent 介绍](https://learn.microsoft.com/en-us/archive/msdn-magazine/2019/january/machine-learning-leveraging-the-beliefs-desires-intentions-agent-architecture)。
4. [LLM-based Autonomous Agents Survey](https://arxiv.org/abs/2308.11432)。

这一轮读完后，应能回答：

- 哪些能力应该交给模型，哪些必须由软件边界约束？
- 为什么“完美 Agent”不是好的工程目标？
- 为什么 Runtime Core 应该小而稳，而不是一开始做大框架？
- 当前项目的实践哪些是可沉淀经验，哪些只是探索样本？

## 十三、阅读笔记模板

为了避免阅读停留在“看过”，建议每篇资料都按同一个模板记录。

```markdown
## 资料名称

- 链接：
- 类型：论文 / 官方文档 / 工程文章 / 框架文档 / 思想文章
- 推荐级别：必读 / 建议读 / 进阶读 / 可选读

### 核心观点

用 3-5 条说明这篇资料真正解决什么问题。

### 和当前项目的关系

它对应当前项目中的哪些实践或问题：

- Context Builder
- Memory / State
- Checkpoint / Resume
- Schema Artifact
- Trace / Replay
- Tool Policy
- Code Review Mini
- D-lite

### 可以吸收的设计

列出可以进入当前 Runtime Core 或后续项目的设计点。

### 需要警惕的地方

列出不适合直接照搬的地方，例如成本太高、场景假设过强、缺少工程边界。

### 后续验证想法

写一个最小可验证实验，而不是宏大的产品目标。
```

这个模板的重点是把阅读转化为工程问题：

```text
读到一个概念 -> 找到当前项目对应问题 -> 设计最小验证 -> 记录结果
```

## 十四、阶段性判断

当前阶段最重要的结论是：Agent 开发正在从“模型调用”走向“运行时系统开发”。这类系统的核心不只是模型能力，而是模型、工具、上下文、状态、记忆、产物、trace、评估和人工介入之间的组织方式。

后续学习可以沿着两条线并行：

第一条是研究线：

```text
[ReAct](https://arxiv.org/abs/2210.03629) -> [Toolformer](https://arxiv.org/abs/2302.04761) -> [Reflexion](https://arxiv.org/abs/2303.11366) -> [Generative Agents](https://arxiv.org/abs/2304.03442) -> [Voyager](https://arxiv.org/abs/2305.16291) -> [SWE-agent](https://arxiv.org/abs/2405.15793) -> [Agent Evaluation](https://arxiv.org/abs/2503.16416)
```

第二条是工程线：

```text
Context Builder -> Memory Store -> Checkpoint / Resume -> Artifact Handoff -> Trace / Replay -> Tool Policy -> Runtime Core
```

两条线都不能单独完成理解。只读论文会低估工程摩擦，只做 demo 会缺少理论坐标。当前项目最有价值的方向，是继续把外部经典思想转化为小范围、可运行、可复盘的实践。

一个更稳的后续目标不是“做一个通用完美 Agent 框架”，而是：

```text
持续识别 Agent 项目中的非功能性关键能力，
把它们从业务代码中隔离出来，
在具体场景中验证这些公共能力是否真的降低复杂度。
```

这也是 Runtime Core 继续存在的意义。

## 参考资料

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [Kaggle / Google: Agents Whitepaper](https://www.kaggle.com/whitepaper-agents)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Google Research Blog: ReAct](https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/)
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)
- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- [Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)
- [Voyager Project Page](https://voyager.minedojo.org/)
- [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155)
- [Microsoft Research: AutoGen](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/)
- [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- [A Survey on Large Language Model based Autonomous Agents](https://arxiv.org/abs/2308.11432)
- [Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416)
- [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangChain / Deep Agents Memory](https://docs.langchain.com/oss/python/deepagents/long-term-memory)
- [LangChain Memory Overview](https://docs.langchain.com/oss/python/concepts/memory)
- [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/)
- [Langfuse Documentation](https://langfuse.com/docs/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Arize Phoenix Documentation](https://arize.com/docs/phoenix)
- [AgentOps Documentation](https://docs.agentops.ai/v2/usage/tracking-agents)
- [AgentTrace: A Structured Logging Framework for Agent System Observability](https://arxiv.org/abs/2602.10133)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/index)
- [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
- [Software 2.0](https://karpathy.github.io/2017/11/11/software2/)
- [Microsoft Learn: Leveraging the Beliefs-Desires-Intentions Agent Architecture](https://learn.microsoft.com/en-us/archive/msdn-magazine/2019/january/machine-learning-leveraging-the-beliefs-desires-intentions-agent-architecture)
