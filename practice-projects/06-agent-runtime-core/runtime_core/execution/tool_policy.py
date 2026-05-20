from __future__ import annotations

"""最小工具策略检查。

阶段 6 只需要演示 Runtime 可以在工具调用前做治理判断。这里不实现工具执行、
审批流或权限系统，只判断一次工具调用是否允许继续。
"""

from enum import Enum

from pydantic import BaseModel, Field


class ToolRiskLevel(str, Enum):
    """工具风险等级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolPolicy(BaseModel):
    """工具的最小治理策略。"""

    tool_name: str = Field(description="工具名称。")
    risk_level: ToolRiskLevel = Field(default=ToolRiskLevel.LOW, description="工具风险等级。")
    read_only: bool = Field(default=True, description="工具是否只读。")
    requires_approval: bool = Field(default=False, description="调用前是否需要人工审批。")


class ToolCallRequest(BaseModel):
    """一次工具调用请求摘要。"""

    tool_name: str = Field(description="工具名称。")
    step_id: str = Field(description="发起调用的 step。")
    mutating: bool = Field(default=False, description="是否会产生写入或副作用。")
    approved: bool = Field(default=False, description="是否已经获得人工审批。")


class ToolPolicyDecision(BaseModel):
    """工具策略检查结果。"""

    allowed: bool = Field(description="是否允许调用。")
    reason: str = Field(description="允许或拒绝原因。")
    risk_level: ToolRiskLevel = Field(description="工具风险等级。")


class ToolPolicyChecker:
    """按工具名执行最小策略检查。"""

    def __init__(self, policies: list[ToolPolicy]) -> None:
        self._policies = {policy.tool_name: policy for policy in policies}

    def check(self, request: ToolCallRequest) -> ToolPolicyDecision:
        policy = self._policies.get(request.tool_name)
        if not policy:
            return ToolPolicyDecision(
                allowed=False,
                reason=f"tool is not registered: {request.tool_name}",
                risk_level=ToolRiskLevel.HIGH,
            )
        if policy.read_only and request.mutating:
            return ToolPolicyDecision(
                allowed=False,
                reason=f"read-only tool cannot run mutating request: {request.tool_name}",
                risk_level=policy.risk_level,
            )
        if policy.requires_approval and not request.approved:
            return ToolPolicyDecision(
                allowed=False,
                reason=f"tool requires approval: {request.tool_name}",
                risk_level=policy.risk_level,
            )
        return ToolPolicyDecision(
            allowed=True,
            reason="tool call allowed by policy",
            risk_level=policy.risk_level,
        )
