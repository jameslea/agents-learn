# Agent 开发能力定位与面试准备

> 更新时间：2026-05-21
>
> 本文用于记录读完 Agent 必读资料后，在 Agent 开发能力、工程判断和面试准备方面大致能达到什么程度。它不是岗位保证，也不是能力认证，而是帮助后续学习时判断“哪些已经具备初步认识，哪些还需要继续强化”。

## 目录

- [一、总体判断](#一总体判断)
- [二、读完必读资料后能达到的能力](#二读完必读资料后能达到的能力)
- [三、仍然不够的地方](#三仍然不够的地方)
- [四、面试 Agent 开发岗的现实定位](#四面试-agent-开发岗的现实定位)
- [五、最值得继续强化的方向](#五最值得继续强化的方向)
- [六、阅读节奏与面试应急策略](#六阅读节奏与面试应急策略)
- [七、面试表达建议](#七面试表达建议)
- [八、阶段性结论](#八阶段性结论)

## 一、总体判断

读完 [Agent 深度学习阅读路线](./agent-reading-roadmap.md) 中标记为“必读”的资料，并且结合当前项目已经完成的多轮实践，可以达到：

```text
理解 Agent 工程核心问题，
能够设计和实现中小型 Agent 系统原型，
并具备向生产级 Agent Runtime 演进的工程意识。
```

但这还不等于已经能独立开发成熟的生产级 Agent 产品。生产级 Agent 不只是一个 prompt、一个模型和几个工具调用，它需要上下文治理、状态恢复、工具权限、结构化产物、trace 复盘、评估体系、成本延迟控制、安全边界和部署治理等一整套工程能力。

因此，更准确的定位是：

```text
已经进入 Agent 工程化学习和实践的核心区间，
但还需要通过真实场景继续补齐框架实战、系统设计和生产化经验。
```

## 二、读完必读资料后能达到的能力

### 1. 能区分 workflow 和 agent

这是最重要的基础判断之一。

读完 [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 后，应该能说明白：

- 固定、可预测、可拆分的任务，优先使用 workflow。
- 需要动态探索、反馈调整和多步决策的任务，才更适合引入 agent。
- 不应该为了“看起来智能”而把所有任务都做成自主 Agent。

这个判断能避免很多 Agent 项目从一开始就陷入复杂性。很多真实业务并不需要通用自主 Agent，低代码工作流、状态机、编排式流程就可以覆盖大部分需求。

### 2. 能理解 Agent 的基础运行循环

读完 [ReAct](https://arxiv.org/abs/2210.03629)、[Toolformer](https://arxiv.org/abs/2302.04761)、[Reflexion](https://arxiv.org/abs/2303.11366) 后，应该能理解 Agent 不是一次性生成答案，而是一个循环过程：

```text
理解任务 -> 选择行动 -> 调用工具 -> 观察结果 -> 更新判断 -> 继续行动或停止
```

这对应了 Thought / Action / Observation 的基础结构，也解释了为什么 Agent 系统必须处理：

- 工具调用失败；
- 观察结果不符合预期；
- 多轮尝试后的策略调整；
- 失败后的反思和经验沉淀；
- 明确停止条件，避免无限循环。

### 3. 能理解上下文、记忆、状态和产物的区别

当前项目已经围绕 Context Builder、Memory / State、Checkpoint / Resume、Schema Artifact、Trace 做了 Runtime Core 实践。结合 [Lost in the Middle](https://arxiv.org/abs/2307.03172)、[Generative Agents](https://arxiv.org/abs/2304.03442)、[Voyager](https://arxiv.org/abs/2305.16291) 这些资料后，应该能建立更清楚的边界：

| 概念 | 核心问题 |
|------|----------|
| Context | 当前这一步应该给模型看什么，如何防止污染和膨胀。 |
| Memory | 哪些经验值得长期保存，如何检索、验证、过期。 |
| State | 当前任务执行到哪里，如何 checkpoint、resume、blocked。 |
| Artifact | Agent 之间或步骤之间交接什么结构化产物。 |
| Trace | 如何记录过程，使失败后能够复盘。 |

这意味着不会把所有东西都塞进 prompt，也不会把所有历史都叫作“记忆”。

### 4. 能设计一个可解释的小型 Agent Runtime

结合当前 Runtime Core 实践和工程文档，应该可以设计一个小型、可解释的 Agent Runtime 原型。它至少包括：

- Context Builder：构造当前步骤的工作视图。
- Tool Policy：限制工具可用范围和高风险操作。
- Runtime State：记录任务、步骤、状态转换和 blocked 原因。
- Checkpoint / Resume：支持长任务恢复。
- Artifact Store：保存结构化产物。
- Trace Recorder：记录 step、tool call、artifact、error。
- Guardrail：处理输入、输出或工具调用的风险。

这类 Runtime Core 的价值不在于一次性做成通用框架，而在于把 Agent 项目中反复出现的非功能能力识别出来，并从具体业务逻辑中隔离出来。

### 5. 能看懂主流框架和平台的设计取舍

读完这些资料并结合实践后，应该能比较理性地看待不同平台：

- LangGraph 更偏状态机、checkpoint 和可恢复执行。
- OpenAI Agents SDK 更强调 agent、handoff、guardrail、trace 等工程构件。
- CrewAI / AutoGen 更偏多角色、多 Agent 协作。
- Dify / Coze / n8n 更偏 workflow 和低代码编排。
- Manus 更接近云端通用自主 Agent 产品。
- Claude Code / Codex CLI 更接近本地开发环境中的代码 Agent。

这时判断一个框架时，不会只问“哪个更火”，而会问：

- 它解决的是 workflow、agentic workflow，还是 autonomous agent？
- 它的状态模型是什么？
- 它如何处理工具权限？
- 它如何 trace 和 replay？
- 它如何支持人工介入？
- 它适合原型、团队内部工具，还是生产级系统？

## 三、仍然不够的地方

### 1. 真实项目落地经验仍然需要继续积累

面试中经常会问：

- 你做过什么 Agent？
- 为什么这个场景需要 Agent，而不是普通 workflow？
- 如何处理失败和重试？
- 如何防止无限循环？
- 如何控制工具权限？
- 如何评估 Agent 输出质量？
- 如何降低成本和延迟？
- 如何处理上下文污染和记忆过期？

这些问题不能只靠论文回答，需要结合项目经验。当前项目已经有很多实践，但其中一部分是探索性、实验性和阶段性产物，还需要继续沉淀出更稳定的案例。

### 2. 框架实战能力还需要补齐

如果目标是 Agent 开发岗，至少需要熟悉一到两个主流框架或平台：

- LangGraph；
- OpenAI Agents SDK；
- LlamaIndex；
- AutoGen / CrewAI；
- Dify / Coze / n8n。

不一定要全部精通，但需要能讲清楚：

- 框架抽象了什么；
- 哪些问题它解决得好；
- 哪些地方仍然需要自己补；
- 和自己项目中的 Runtime Core 思路有什么异同。

### 3. LLM 应用工程能力需要继续强化

Agent 开发不是只写 prompt。还需要掌握：

- tool calling / function calling；
- structured output；
- RAG；
- prompt 版本管理；
- eval；
- tracing；
- provider 抽象；
- token、latency 和 retry 控制；
- 多模型切换；
- 缓存和成本治理。

这些能力决定了 Agent 原型能否稳定走向可用系统。

### 4. 软件工程基本功仍然是基础

Agent 岗位本质上仍然是软件开发岗位，只是系统中多了不确定的模型能力。因此仍然需要：

- Python / TypeScript 工程能力；
- API 设计；
- 异步任务；
- 数据存储；
- 测试；
- 日志；
- 权限；
- 部署；
- 监控；
- 安全治理。

没有这些能力，Agent 系统很容易停留在 demo 阶段。

## 四、面试 Agent 开发岗的现实定位

如果面试的是偏 **LLM 应用开发 / Agent 原型开发 / AI 应用工程师** 的岗位，当前学习路线和项目实践会比较有竞争力。

这种岗位通常更看重：

- 是否理解 LLM 应用开发；
- 是否能把模型能力接入具体业务；
- 是否能构造工具调用和工作流；
- 是否能处理上下文、结构化输出和失败重试；
- 是否能快速做出可运行原型。

如果面试的是偏 **Agent 平台 / Agent Runtime / AI Infra / 企业级 Agent 系统** 的岗位，还需要继续补强工程深度，尤其是：

- 长任务状态管理；
- 多租户和权限系统；
- trace / eval 平台；
- 工具沙箱；
- 人工审批流；
- 成本治理；
- 部署和运维；
- 安全、审计和合规。

这类岗位更接近平台工程和基础设施工程，要求会明显更高。

## 五、最值得继续强化的方向

后续最有价值的准备，不是泛泛读更多资料，而是围绕一个能讲清楚的面试作品继续强化。

这个作品最好具备：

- 一个具体 Agent 场景；
- 明确说明为什么使用 workflow、agentic workflow 或 autonomous agent；
- 有 Context Builder；
- 有 tool calling；
- 有结构化 artifact；
- 有 checkpoint / resume；
- 有 trace；
- 有失败处理和 blocked 状态；
- 有简单 eval 或 replay；
- 有 README 说明架构取舍。

这样面试时就不是只讲概念，而是可以讲清楚：

- 为什么这么设计；
- 曾经遇到什么问题；
- 如何修正；
- 哪些能力是 Agent 系统必须有的；
- 哪些能力当前阶段刻意不做；
- 如果进入生产环境，下一步需要补什么。

## 六、阅读节奏与面试应急策略

如果目标是长期掌握 Agent 开发，这些资料不应该读得太快。论文、官方指南和工程文档的价值不只是记住概念，而是把它们转化成设计判断。

但如果近期要面试，可以采用“两层阅读法”：先用 3-5 天建立面试可表达的工程框架，再用 2-4 周做深度补强。

### 1. 第一层：面试快速阅读，3-5 天

这一层的目标不是吃透论文细节，而是建立能讲清楚的 Agent 工程框架。

推荐顺序如下：

| 顺序 | 资料 | 建议时间 | 面试重点 |
|------|------|----------|----------|
| 1 | [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | 已读，可复盘 0.5 天 | workflow vs agent、常见 workflow 模式、什么时候不要用 agent。 |
| 2 | [OpenAI: A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) | 0.5-1 天 | agent 定义、tools、handoff、guardrails、tracing。 |
| 3 | [ReAct](https://arxiv.org/abs/2210.03629) | 0.5 天 | Thought / Action / Observation 循环。 |
| 4 | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 0.5 天 | 长上下文不是越长越好，信息位置会影响模型利用。 |
| 5 | [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 0.5 天 | thread、checkpoint、resume、state。 |
| 6 | [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/) 和 [Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/) | 0.5-1 天 | trace 不是普通日志，guardrail 应覆盖输入、输出和工具调用。 |

读完这一层后，面试中至少应该能讲出一条主线：

```text
Agent 不是一个 prompt，而是由模型、工具、上下文、状态、产物、trace 和 guardrail 组成的运行系统。
实际开发时应先判断 workflow 是否足够，只有任务需要动态探索和反馈调整时，才引入更强的 Agent 自主性。
```

### 2. 第二层：深度补强，2-4 周

这一层的目标是把“能讲”变成“真能设计”。

推荐顺序如下：

| 顺序 | 资料 | 重点 |
|------|------|------|
| 1 | [Toolformer](https://arxiv.org/abs/2302.04761) | 理解工具使用背后的思想，不必深究训练细节。 |
| 2 | [Reflexion](https://arxiv.org/abs/2303.11366) | 理解失败学习、反思记忆和重试策略。 |
| 3 | [Generative Agents](https://arxiv.org/abs/2304.03442) | 理解记忆系统中的事件、检索和反思。 |
| 4 | [Voyager](https://arxiv.org/abs/2305.16291) | 理解长期任务、技能库和经验沉淀。 |
| 5 | [SWE-agent](https://arxiv.org/abs/2405.15793) | 理解代码 Agent 中的 Agent-Computer Interface。 |

这些资料更适合慢慢读，因为它们会影响对 Agent 长期能力、记忆、技能库、代码环境和工具界面的理解。

### 3. 时间非常紧时的最小必读包

如果只为应付近期面试，最小必读包可以压缩为：

1. [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
2. [OpenAI: A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
3. [ReAct](https://arxiv.org/abs/2210.03629)
4. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
5. [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)
6. [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-js/guides/guardrails/)

这 6 个资料加上当前 Runtime Core 项目总结，足以支撑一次中等强度的 Agent 开发岗面试。

### 4. 每篇资料只先回答五个问题

快速阅读时不要逐字读论文。每篇资料先回答五个问题：

1. 它解决什么问题？
2. 它提出了什么核心概念？
3. 它对 Agent 开发有什么启发？
4. 它和当前 Runtime Core 项目哪一部分对应？
5. 面试时能用一句话怎么讲？

例如，ReAct 可以这样准备：

```text
ReAct 的价值是把推理和行动交替起来，让模型不是一次性回答，
而是在 Thought / Action / Observation 循环中调用工具、观察环境并调整下一步行动。
这是很多 Agent Runtime 的基础循环。
```

### 5. 面试前五天建议节奏

如果近期有面试，可以按下面节奏准备：

| 天数 | 任务 |
|------|------|
| 第 1 天 | 复盘 01，阅读 02。 |
| 第 2 天 | 阅读 ReAct 和 Lost in the Middle。 |
| 第 3 天 | 阅读 LangGraph Persistence、OpenAI Tracing 和 Guardrails。 |
| 第 4 天 | 整理 8-10 个面试问题答案。 |
| 第 5 天 | 用当前 Runtime Core 项目完整串讲一遍。 |

如果没有紧急面试，可以每周读 2 篇，每篇写一页中文导读。每读完一篇，都补充“对 Runtime Core 的启发”。这样 4-6 周可以形成相当扎实的 Agent 工程知识体系。

## 七、面试表达建议

可以把自己的能力表述为：

```text
熟悉 Agent 核心范式，理解 workflow 与 autonomous agent 的边界，
能够设计和实现具备上下文管理、工具调用、状态恢复、结构化产物、
trace 复盘和基础 guardrail 的 Agent 应用原型，
并具备向生产级 Agent Runtime 演进的工程意识。
```

这个表述比“我会开发 Agent”更具体，也更容易展开。

在面试中，可以主动强调：

- 不会默认把所有任务都做成自主 Agent；
- 会优先判断任务边界和流程稳定性；
- 会把业务逻辑和非功能治理能力拆开；
- 会关注 trace、eval、权限、状态恢复，而不是只关注模型回答；
- 会根据场景选择 workflow、agentic workflow 或 autonomous agent。

这类表达能体现对 Agent 工程复杂度的真实理解。

## 八、阶段性结论

读完必读资料之后，最重要的收获不是知道更多名词，而是形成一组判断：

```text
Agent 不是越自主越好；
workflow 不是低级形态；
工具调用不是简单 API 封装；
记忆不是无限历史记录；
trace 不是普通日志；
Runtime Core 不是业务逻辑替代品；
生产级 Agent 是模型能力与软件工程边界的结合。
```

当前学习已经从“了解 Agent 概念”进入“理解 Agent 系统工程边界”的阶段。后续应该继续读必读资料中未完成的部分，同时围绕一个具体场景做小步验证，把理论、文档和项目经验逐步对齐。
