from __future__ import annotations

"""任务契约定义。

TaskContract 是 Runtime 的入口协议，用来在执行前明确：
任务类型、目标、输入、期望产物、成功标准、风险等级、允许工具和预算。
它的作用是避免 Agent 只拿一段自然语言目标就直接自由发挥。

主要类与关系：
- RiskLevel：任务和工具共享的风险等级枚举，供 TaskContract 与 ToolSpec 使用。
- TaskType：任务类型枚举，用来区分 self-heal、RAG、研究、文档治理等场景。
- HumanReviewPolicy：描述任务是否需要人工确认，后续会和 needs_human 终态配合。
- Budget：任务预算约束，包括最大尝试次数、超时、模型调用次数和工具调用次数。
- TaskContract：Runtime 的任务入口。scenario / adapter 先创建它，再交给工具治理、
  trace、artifact 和 evaluation 模块使用。

典型关系：
TaskContract -> ToolPolicy.from_contract(...) -> GovernedToolRunner
TaskContract -> Artifact.task_id / EvaluationResult.task_id / TraceEvent.payload
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """任务或工具的风险等级。

    - LOW：低风险。只读、分析、统计、格式检查等不会产生外部副作用的动作。
    - MEDIUM：中风险。可能修改临时工作区、执行受限代码或消耗明显资源的动作。
    - HIGH：高风险。可能写入真实文件、联网、调用外部系统、发布内容或产生不可逆副作用的动作。
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    """Runtime 当前支持的任务类型。

    - SELF_HEAL：代码执行、自愈修复和安全拦截任务。
    - RAG_QA：知识库问答、检索准备度或 RAG 评估任务。
    - RESEARCH：自主调研、任务循环和研究报告任务。
    - CONTENT_GENERATION：内容创作、报告生成和质量评审任务。
    - MULTIMODAL_UNDERSTANDING：图片、语音、视频等多模态理解任务。
    - DOCUMENT_GOVERNANCE：文档质量治理、问题提取和改进计划任务。
    """

    SELF_HEAL = "self_heal"
    RAG_QA = "rag_qa"
    RESEARCH = "research"
    CONTENT_GENERATION = "content_generation"
    MULTIMODAL_UNDERSTANDING = "multimodal_understanding"
    DOCUMENT_GOVERNANCE = "document_governance"


class HumanReviewPolicy(str, Enum):
    """人工介入策略。

    - NEVER：不主动请求人工确认，适合低风险只读任务。
    - ON_HIGH_RISK：遇到高风险工具、低置信度结果或发布动作时请求人工确认。
    - ALWAYS：每次关键动作都需要人工确认，适合审计、发布和高风险实验。
    """

    NEVER = "never"
    ON_HIGH_RISK = "on_high_risk"
    ALWAYS = "always"


class Budget(BaseModel):
    """Simple execution budget used by adapters and eval runners."""

    max_attempts: int = 3
    timeout_seconds: float = 5.0
    max_model_calls: int | None = None
    max_tool_calls: int | None = None


class TaskContract(BaseModel):
    """Stable task entry contract.

    Existing practice projects can be wrapped by this model without rewriting
    their internal implementation.
    """

    task_id: str
    task_type: TaskType
    goal: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    allowed_tools: list[str] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    human_review_policy: HumanReviewPolicy = HumanReviewPolicy.NEVER

    @classmethod
    def for_d_lite_task(
        cls,
        task_path: Path,
        *,
        max_attempts: int = 3,
        timeout_seconds: float = 5.0,
    ) -> "TaskContract":
        """Create a self-healing contract for one D-lite challenge task."""
        return cls(
            task_id=f"d_lite:{task_path.name}",
            task_type=TaskType.SELF_HEAL,
            goal=f"Repair and verify D-lite challenge task {task_path.name}.",
            inputs={"task_path": str(task_path)},
            expected_outputs=["CodeRepairArtifact", "ErrorSummaryArtifact", "EvaluationResult"],
            success_criteria=[
                "verification command passes",
                "dangerous code is blocked instead of executed",
                "final status is backed by objective verification",
            ],
            risk_level=RiskLevel.MEDIUM,
            allowed_tools=[
                "d_lite.run_self_heal",
                "d_lite.prepare_workspace",
                "d_lite.verify_python_file",
                "d_lite.repair_agent",
                "d_lite.ast_checker",
            ],
            budget=Budget(max_attempts=max_attempts, timeout_seconds=timeout_seconds),
            human_review_policy=HumanReviewPolicy.ON_HIGH_RISK,
        )
