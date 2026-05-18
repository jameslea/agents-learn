# Agent Runtime 实践观察报告

## 1. 背景

前面的 Agent 实践说明，单纯增加角色或工具并不能自然提升系统可靠性。更关键的问题是：任务目标是否清楚、产物是否结构化、过程是否可回放、工具是否有权限边界。

Agent Runtime & Governance Lab 的目标不是替代 LangGraph、Dify、Coze 或其他平台，而是把学习项目中反复出现的非功能能力抽出来，做成一个可以观察、验证和回归的最小系统。这个系统应优先回答“任务如何定义”“结果如何证明”“工具如何约束”“失败如何复盘”这些问题。

在这个阶段，Runtime 的价值主要体现在三个层面。第一，给每个任务建立明确的 contract，避免 Agent 只靠自然语言目标自由发挥。第二，把中间结果保存为 artifact，让下游步骤读取结构化产物，而不是读取长对话历史。第三，把模型调用、工具调用、验证和评估写入 trace，让每一次成功或失败都有证据链。

## 2. 核心发现

- 多角色协作容易退化成 prompt 接龙。
- 自主循环必须有预算和停止条件。
- 自愈任务不能相信 Agent 的解释，必须依赖客观验证。
- Runtime 应该把状态、工具、产物、评估和 trace 从业务逻辑中抽离出来。
- ToolPolicy 应当先于工具调用存在，而不是在事故发生后补救。
- EvaluationResult 应该成为每个任务的稳定出口，而不是临时打印日志。
- Human-in-the-loop 应该是状态机的一部分，而不是散落在流程里的手动确认。

## 3. 证据

| 项目 | 观察 |
|------|------|
| B 内容团队 | 报告质量受结构、引用和评审标准影响明显 |
| C 自主调研 | 任务队列、反思和成本控制是稳定性的基础 |
| D-lite 自愈 | 安全拦截和验证命令比自然语言解释更可靠 |

这些证据不是为了证明某个具体框架优于另一个框架，而是为了证明：当任务变复杂时，Agent 的主要难点会从 prompt 设计转向 runtime 设计。B 项目中的报告质量问题，说明评估标准必须提前结构化；C 项目中的目标漂移和预算问题，说明长任务必须有状态和熔断；D-lite 中的危险代码拦截，说明工具权限必须在执行前生效。

可参考资料：

- https://github.com/langchain-ai/langgraph
- https://github.com/langfuse/langfuse
- https://github.com/Arize-ai/phoenix
- https://modelcontextprotocol.io/
- https://docs.pydantic.dev/

- [Agent Runtime 哲学](../../../docs/concepts/agent-runtime-philosophy.md)
- [Agent 框架与服务选型地图](../../../docs/concepts/agent-frameworks-and-services-landscape.md)
- [多模态 Agent 能力地图](../../../docs/concepts/multimodal-agent-capabilities-landscape.md)
- [项目开发计划](../../../docs/agent-runtime-governance-development-plan.md)
- [D-lite README](../04-self-healing-ops/README.md)

## 4. 局限与证据边界

这些观察来自本仓库的学习项目，不等同于生产环境结论。当前样本数量有限，评估指标也偏确定性规则，尚未覆盖真实用户反馈、长期运行稳定性和复杂多租户场景。

还有几个边界需要明确。第一，当前 Runtime Lab 不是生产级框架，不能直接用于高风险线上任务。第二，当前文档治理场景主要使用确定性规则，尚未引入人工审阅和 LLM reviewer 的交叉验证。第三，旧项目 adapter 只能作为回归样本，不能成为项目 E 的主体。第四，多模态、小模型和外部观测平台都应作为后续扩展，不应阻塞核心模型的稳定。

这些局限本身也应该被纳入 trace 和 evaluation。一个可维护的 Agent 系统不应该只记录成功样本，也要记录失败、阻塞、人工确认和不确定性来源。

## 5. 建议

- 先实现独立 Runtime Core，再接入旧项目作为回归样本。
- 每个 Agent 任务都应先生成 TaskContract。
- 每个关键步骤都应生成 Artifact。
- 每次工具调用都应进入 Trace。
- 高风险工具必须由 ToolPolicy 管理。
- 每个 EvaluationResult 都应包含评分、失败原因和可追踪指标。
- 对于质量不足的产物，应生成 IssueArtifact 和 ImprovementPlanArtifact。
- 对于高风险动作，应返回 blocked 或 needs_human，而不是继续自动执行。

## 6. 后续实施路径

第一阶段应围绕文档治理、代码自愈和 RAG readiness 这三类任务建立最小闭环。文档治理用于观察结构、证据和改进计划；代码自愈用于观察工具安全、验证和 blocked 终态；RAG readiness 用于观察数据资产、索引资产和关键测试证据。

第二阶段可以增加 Tool Registry、HumanReviewRequest、HumanReviewDecision 和跨项目评估报告。这个阶段的重点不是增加更多 Agent，而是让现有能力在同一个 runtime 协议下运行。

第三阶段再引入多模态和小模型能力。例如，图片/OCR 工具可以生成 ImageUnderstandingArtifact，ASR 工具可以生成 TranscriptArtifact，编码小模型可以作为低风险 worker 处理局部代码修复。所有这些能力都必须通过 TaskContract、ToolPolicy、Artifact、Trace 和 Evaluation 接入。
