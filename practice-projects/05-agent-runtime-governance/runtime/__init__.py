"""Agent Runtime & Governance 的最小核心模块。

这个包只放和具体业务场景无关的 Runtime Core：
任务契约、结构化产物、AgentAdapter、工具治理、trace 和评估结果。
具体项目或 demo 应通过 adapter / scenario 调用这些能力，而不是把业务逻辑写进 runtime。

模块关系：
- contracts：定义任务入口 TaskContract。
- state：定义 RuntimeState 和 StepExecution，记录任务步骤、状态值和产物引用。
- agent_adapter：定义不同 Agent 项目接入 Runtime 的最小协议和统一生命周期。
- tools：根据 TaskContract 生成 ToolPolicy，并通过 GovernedToolRunner 受控调用工具。
- artifacts：保存工具、Agent、验证器产生的结构化产物。
- trace：记录任务、工具、产物和评估事件，保证过程可回放。
- manifest：记录一次运行的 trace、checkpoint、artifact root 和最终状态。
- evaluation：输出统一 EvaluationResult 和批量 EvaluationSummary。

推荐数据流：
AgentAdapter -> TaskContract -> RuntimeState / StepExecution -> Tool -> Artifact -> Trace -> EvaluationResult
"""
