from __future__ import annotations

"""工具治理与受控调用。

ToolRegistry 记录 Runtime 已知工具，ToolPolicy 描述当前任务允许调用哪些工具，
GovernedToolRunner 在真正执行工具前做权限、风险等级和调用次数检查。
这个模块的目标是让工具调用成为可治理的 runtime 行为，而不是普通函数调用。

主要类与关系：
- ToolSpec：工具元数据，描述工具名、用途、风险等级、输入输出 schema、是否需要审批、
  最大调用次数、读写路径入参、是否需要网络等。它是工具进入 Runtime 的登记表。
- ToolRegistry：工具注册表，维护 ToolSpec 与真实 handler 的映射。
- ToolPolicy：某个任务当前允许的工具策略，通常由 TaskContract.allowed_tools 生成。
- GovernedToolRunner：唯一推荐的工具调用入口。它先检查 ToolPolicy，再调用 ToolRegistry
  中的 handler，并把调用事件写入 trace。
- ToolCallBlocked：工具被策略拦截时抛出的异常，携带 ToolDecisionArtifact。
- ToolNeedsHumanReview：工具在任务范围内但需要人工审核时抛出的异常。

典型关系：
TaskContract.allowed_tools -> ToolPolicy
ToolSpec + handler -> ToolRegistry
ToolRegistry + ToolPolicy + RuntimeTraceRecorder -> GovernedToolRunner
GovernedToolRunner.call(...) -> tool handler -> Artifact / metrics
"""

from collections import Counter
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from runtime.artifacts import ToolDecision, ToolDecisionArtifact
from runtime.contracts import RiskLevel, TaskContract
from runtime.trace import RuntimeTraceRecorder, TraceEventType


class ToolSpec(BaseModel):
    """Runtime metadata for one callable capability."""

    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    input_schema: str = "dict"
    output_schema: str = "dict"
    approval_required: bool = False
    max_calls: int | None = None
    read_path_args: list[str] = Field(default_factory=list)
    write_path_args: list[str] = Field(default_factory=list)
    requires_network: bool = False


class ToolCallBlocked(Exception):
    """Raised when runtime policy blocks a tool call."""

    def __init__(self, decision: ToolDecisionArtifact):
        super().__init__(decision.reason)
        self.decision = decision


class ToolNeedsHumanReview(Exception):
    """Raised when a tool call needs human approval before execution."""

    def __init__(self, decision: ToolDecisionArtifact):
        super().__init__(decision.reason)
        self.decision = decision


class ToolRegistry:
    """In-memory tool registry for the minimal runtime."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, Callable[..., Any]]] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Any]) -> None:
        self._tools[spec.name] = (spec, handler)

    def spec(self, name: str) -> ToolSpec:
        return self._tools[name][0]

    def handler(self, name: str) -> Callable[..., Any]:
        return self._tools[name][1]

    def names(self) -> list[str]:
        return sorted(self._tools)


class ToolPolicy(BaseModel):
    """Runtime policy applied before tool execution."""

    allowed_tools: list[str] = Field(default_factory=list)
    allow_high_risk: bool = False
    approved_tools: list[str] = Field(default_factory=list)
    allowed_read_dirs: list[str] = Field(default_factory=list)
    allowed_write_dirs: list[str] = Field(default_factory=list)
    allow_network: bool = False
    max_calls_per_tool: int = 5

    @classmethod
    def from_contract(
        cls,
        contract: TaskContract,
        *,
        allowed_read_dirs: list[str] | None = None,
        allowed_write_dirs: list[str] | None = None,
        allow_network: bool = False,
    ) -> "ToolPolicy":
        return cls(
            allowed_tools=contract.allowed_tools,
            allowed_read_dirs=allowed_read_dirs or [],
            allowed_write_dirs=allowed_write_dirs or [],
            allow_network=allow_network,
        )

    def model_summary(self) -> dict[str, Any]:
        return {
            "allowed_tools": self.allowed_tools,
            "allow_high_risk": self.allow_high_risk,
            "approved_tools": self.approved_tools,
            "allowed_read_dirs": self.allowed_read_dirs,
            "allowed_write_dirs": self.allowed_write_dirs,
            "allow_network": self.allow_network,
            "max_calls_per_tool": self.max_calls_per_tool,
        }


class GovernedToolRunner:
    """Executes registered tools only after policy checks."""

    def __init__(
        self,
        registry: ToolRegistry,
        policy: ToolPolicy,
        trace: RuntimeTraceRecorder,
        task_id: str,
    ) -> None:
        self.registry = registry
        self.policy = policy
        self.trace = trace
        self.task_id = task_id
        self.calls: Counter[str] = Counter()

    def call(self, tool_name: str, **kwargs: Any) -> Any:
        spec = self.registry.spec(tool_name)
        decision = self._decide(spec, kwargs)
        self.trace.record(TraceEventType.TOOL_DECISION, decision)
        if decision.decision == ToolDecision.BLOCKED:
            self.trace.record(TraceEventType.GUARDRAIL_BLOCKED, decision)
            raise ToolCallBlocked(decision)
        if decision.decision == ToolDecision.NEEDS_HUMAN:
            self.trace.record(TraceEventType.HUMAN_REVIEW_REQUESTED, decision)
            raise ToolNeedsHumanReview(decision)

        self.calls[tool_name] += 1
        self.trace.record(
            TraceEventType.TOOL_CALLED,
            {
                "task_id": self.task_id,
                "tool_name": tool_name,
                "risk_level": spec.risk_level.value,
                "inputs": kwargs,
            },
        )
        return self.registry.handler(tool_name)(**kwargs)

    def _decide(self, spec: ToolSpec, inputs: dict[str, Any]) -> ToolDecisionArtifact:
        decision = ToolDecision.ALLOWED
        reason = f"Tool allowed by current runtime policy: {spec.name}"
        limit = spec.max_calls or self.policy.max_calls_per_tool

        if spec.name not in self.policy.allowed_tools:
            decision = ToolDecision.BLOCKED
            reason = f"Tool is not allowed by contract: {spec.name}"
        elif self.calls[spec.name] >= limit:
            decision = ToolDecision.BLOCKED
            reason = f"Tool call limit exceeded for {spec.name}: {limit}"
        else:
            scope_error = _scope_error(spec, inputs, self.policy)
            if scope_error:
                decision = ToolDecision.BLOCKED
                reason = scope_error
            elif spec.requires_network and not self.policy.allow_network:
                decision = ToolDecision.BLOCKED
                reason = f"Tool requires network but network access is not allowed: {spec.name}"
            elif spec.approval_required and spec.name not in self.policy.approved_tools:
                decision = ToolDecision.NEEDS_HUMAN
                reason = f"Tool requires human approval before execution: {spec.name}"
            elif spec.risk_level == RiskLevel.HIGH and not self.policy.allow_high_risk:
                decision = ToolDecision.BLOCKED
                reason = f"High-risk tool is not enabled by current policy: {spec.name}"

        return ToolDecisionArtifact(
            artifact_id=f"{self.task_id}:tool_decision:{spec.name}:{sum(self.calls.values()) + 1}",
            task_id=self.task_id,
            source="tool_policy",
            tool_name=spec.name,
            decision=decision,
            risk_level=spec.risk_level.value,
            reason=reason,
            approval_required=spec.approval_required,
            policy=self.policy.model_summary(),
            inputs_summary=_summarize_inputs(inputs),
        )


def _summarize_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in inputs.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            summary[key] = value
        elif isinstance(value, list):
            summary[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            summary[key] = f"dict[{len(value)}]"
        else:
            summary[key] = type(value).__name__
    return summary


def _scope_error(spec: ToolSpec, inputs: dict[str, Any], policy: ToolPolicy) -> str | None:
    for arg_name in spec.read_path_args:
        error = _path_scope_error(
            tool_name=spec.name,
            arg_name=arg_name,
            path_value=inputs.get(arg_name),
            allowed_dirs=policy.allowed_read_dirs,
            access_kind="read",
        )
        if error:
            return error
    for arg_name in spec.write_path_args:
        error = _path_scope_error(
            tool_name=spec.name,
            arg_name=arg_name,
            path_value=inputs.get(arg_name),
            allowed_dirs=policy.allowed_write_dirs,
            access_kind="write",
        )
        if error:
            return error
    return None


def _path_scope_error(
    *,
    tool_name: str,
    arg_name: str,
    path_value: Any,
    allowed_dirs: list[str],
    access_kind: str,
) -> str | None:
    if path_value is None:
        return f"Tool {tool_name} requires path argument '{arg_name}' for {access_kind} scope check."
    if not allowed_dirs:
        return f"Tool {tool_name} has no allowed {access_kind} directories for argument '{arg_name}'."

    candidate = Path(str(path_value)).expanduser().resolve()
    allowed_paths = [Path(directory).expanduser().resolve() for directory in allowed_dirs]
    if any(_is_within(candidate, allowed) for allowed in allowed_paths):
        return None
    return (
        f"Tool {tool_name} {access_kind} path is outside allowed scope: "
        f"{arg_name}={candidate}; allowed={allowed_paths}"
    )


def _is_within(candidate: Path, directory: Path) -> bool:
    return candidate == directory or directory in candidate.parents
