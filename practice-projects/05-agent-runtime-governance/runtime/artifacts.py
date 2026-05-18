from __future__ import annotations

"""结构化产物定义。

Artifact 是 Runtime 中步骤之间传递信息的稳定载体。
Agent、工具和评估器不应只依赖长对话或自由文本交接，
而应把关键结果保存为可校验、可追踪、可版本化的 artifact。

主要类与关系：
- ArtifactType：所有 artifact 的类型枚举，用来在 trace 和报告中快速识别产物类别。
- Artifact：所有结构化产物的基类，统一保存 artifact_id、task_id、来源和 metadata。
- ErrorSummaryArtifact / CodeRepairArtifact：服务 D-lite 自愈场景，记录错误摘要和修复结果。
- RAGEvaluationArtifact / ContentReportArtifact / ResearchReportArtifact：服务旧项目 adapter，
  用作 Runtime 的回归样本和兼容性样本。
- DocumentQualityArtifact：Runtime 原生文档治理场景的质量度量产物。
- IssueArtifact：把质量问题转成可追踪、可排序、可修复的结构化问题。
- ImprovementPlanArtifact：根据 IssueArtifact 生成改进计划，作为后续执行或人工审核的输入。
- LLMReviewArtifact：记录可选 LLM reviewer 的结构化意见，只作为辅助信号。
- ToolDecisionArtifact：记录 Runtime 对一次工具调用的治理决策。
- HumanReviewRequestArtifact / HumanReviewDecisionArtifact：记录人工介入请求和人工决策。
- EvaluationArtifact：EvaluationResult 的 artifact 包装，便于进入 trace 和后续报告。

典型关系：
TaskContract.task_id -> Artifact.task_id
Tool output -> DocumentQualityArtifact / IssueArtifact / ImprovementPlanArtifact
Artifact -> RuntimeTraceRecorder.record(ARTIFACT_CREATED, artifact)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactType(str, Enum):
    """Runtime 产物类型。

    - TEXT：通用文本产物，如摘要、说明或报告片段。
    - ERROR_SUMMARY：错误摘要，将 traceback、安全问题或失败原因压缩成稳定结构。
    - CODE_REPAIR：代码修复结果，包括修复摘要、目标文件和最终验证状态。
    - EVALUATION：评估结果的 artifact 包装，便于进入 trace。
    - RAG_EVALUATION：RAG readiness 或检索质量相关产物。
    - CONTENT_REPORT：内容团队报告质量评估产物。
    - RESEARCH_REPORT：自主调研报告结构与风险指标产物。
    - DOCUMENT_QUALITY：Runtime 原生文档治理场景中的质量指标产物。
    - ISSUE：结构化问题，描述质量、安全或治理缺陷。
    - IMPROVEMENT_PLAN：根据问题生成的改进计划。
    - LLM_REVIEW：LLM 审阅意见，作为确定性评估之外的辅助判断。
    - TOOL_DECISION：工具治理决策，说明一次工具调用被允许、拦截或需要人工审核。
    - HUMAN_REVIEW_REQUEST：人工审核请求，说明为什么自动流程不能继续。
    - HUMAN_REVIEW_DECISION：人工审核结果，记录批准、拒绝或要求修改。
    """

    TEXT = "text"
    ERROR_SUMMARY = "error_summary"
    CODE_REPAIR = "code_repair"
    EVALUATION = "evaluation"
    RAG_EVALUATION = "rag_evaluation"
    CONTENT_REPORT = "content_report"
    RESEARCH_REPORT = "research_report"
    DOCUMENT_QUALITY = "document_quality"
    ISSUE = "issue"
    IMPROVEMENT_PLAN = "improvement_plan"
    LLM_REVIEW = "llm_review"
    TOOL_DECISION = "tool_decision"
    HUMAN_REVIEW_REQUEST = "human_review_request"
    HUMAN_REVIEW_DECISION = "human_review_decision"


class Artifact(BaseModel):
    """Base artifact metadata shared by all structured outputs."""

    artifact_id: str
    artifact_type: ArtifactType
    task_id: str
    created_at: str = Field(default_factory=utc_now)
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorSummaryArtifact(Artifact):
    """Compressed error evidence from a failed verification attempt."""

    artifact_type: ArtifactType = ArtifactType.ERROR_SUMMARY
    error_kind: str
    message: str
    evidence: str = ""
    line_number: int | None = None
    attempt: int | None = None


class CodeRepairArtifact(Artifact):
    """Structured summary of a self-healing repair result."""

    artifact_type: ArtifactType = ArtifactType.CODE_REPAIR
    task_name: str
    final_status: str
    final_reason: str
    attempts: int
    changed: bool
    repair_summaries: list[str] = Field(default_factory=list)
    workspace_path: str = ""
    target_path: str = ""


class EvaluationArtifact(Artifact):
    """Artifact wrapper for machine-readable evaluation output."""

    artifact_type: ArtifactType = ArtifactType.EVALUATION
    status: str
    score: float
    metrics: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class RAGEvaluationArtifact(Artifact):
    """Deterministic project-A readiness and evidence check."""

    artifact_type: ArtifactType = ArtifactType.RAG_EVALUATION
    data_files: list[str] = Field(default_factory=list)
    expected_terms_found: dict[str, bool] = Field(default_factory=dict)
    index_present: bool = False
    notes: list[str] = Field(default_factory=list)


class ContentReportArtifact(Artifact):
    """Structured snapshot of a generated content-team report."""

    artifact_type: ArtifactType = ArtifactType.CONTENT_REPORT
    report_path: str
    total_score: int
    editorial_score: int
    evidence_score: int
    issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)


class ResearchReportArtifact(Artifact):
    """Structured snapshot of an autonomous research report."""

    artifact_type: ArtifactType = ArtifactType.RESEARCH_REPORT
    report_path: str
    chars: int
    headings: int
    bullets: int
    tables: int
    risk_terms: dict[str, int] = Field(default_factory=dict)


class DocumentQualityArtifact(Artifact):
    """Deterministic quality metrics for a standalone markdown document."""

    artifact_type: ArtifactType = ArtifactType.DOCUMENT_QUALITY
    document_path: str
    chars: int
    headings: int
    lists: int
    tables: int
    references: int
    evidence_boundary_mentions: int
    avg_section_chars: float
    thin_sections: int
    metrics: dict[str, Any] = Field(default_factory=dict)


class IssueSeverity(str, Enum):
    """问题严重程度。

    - LOW：低严重度。影响可读性、格式或扫描效率，但不阻塞任务。
    - MEDIUM：中严重度。影响结构、证据边界或结果可信度，需要修复。
    - HIGH：高严重度。缺少关键证据、覆盖不足或存在高风险缺陷，通常会导致评估失败。
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueArtifact(Artifact):
    """A structured, actionable quality or governance issue."""

    artifact_type: ArtifactType = ArtifactType.ISSUE
    issue_id: str
    severity: IssueSeverity
    category: str
    message: str
    evidence: str = ""
    recommendation: str = ""


class ImprovementPlanArtifact(Artifact):
    """Ordered remediation plan generated from issue artifacts."""

    artifact_type: ArtifactType = ArtifactType.IMPROVEMENT_PLAN
    plan_id: str
    summary: str
    steps: list[str] = Field(default_factory=list)
    issue_ids: list[str] = Field(default_factory=list)


class LLMReviewArtifact(Artifact):
    """Auxiliary LLM review that does not decide final pass/fail status."""

    artifact_type: ArtifactType = ArtifactType.LLM_REVIEW
    reviewer_id: str
    provider: str = "unknown"
    model: str = "unknown"
    verdict: str
    confidence: float
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    status: str = "success"
    failure_reason: str = ""
    raw_text: str = ""


class ToolDecision(str, Enum):
    """工具治理决策。

    - ALLOWED：工具调用被当前策略允许，可以继续执行。
    - BLOCKED：工具调用被策略拦截，自动流程不能执行该动作。
    - NEEDS_HUMAN：工具调用本身在任务范围内，但需要人工批准后才能执行。
    """

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"


class ToolDecisionArtifact(Artifact):
    """Structured policy decision for one attempted tool call."""

    artifact_type: ArtifactType = ArtifactType.TOOL_DECISION
    tool_name: str
    decision: ToolDecision
    risk_level: str
    reason: str
    approval_required: bool
    policy: dict[str, Any] = Field(default_factory=dict)
    inputs_summary: dict[str, Any] = Field(default_factory=dict)


class HumanDecision(str, Enum):
    """人工审核决策。

    - APPROVED：人工批准执行该动作。
    - REJECTED：人工拒绝执行该动作。
    - CHANGES_REQUESTED：需要修改计划、输入或风险控制后再提交审核。
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class HumanReviewRequestArtifact(Artifact):
    """Request produced when runtime needs human approval."""

    artifact_type: ArtifactType = ArtifactType.HUMAN_REVIEW_REQUEST
    request_id: str
    tool_name: str
    reason: str
    requested_action: str
    risk_level: str
    inputs_summary: dict[str, Any] = Field(default_factory=dict)


class HumanReviewDecisionArtifact(Artifact):
    """Human approval or rejection attached to a review request."""

    artifact_type: ArtifactType = ArtifactType.HUMAN_REVIEW_DECISION
    request_id: str
    decision: HumanDecision
    reviewer: str = "runtime_cli"
    rationale: str = ""
