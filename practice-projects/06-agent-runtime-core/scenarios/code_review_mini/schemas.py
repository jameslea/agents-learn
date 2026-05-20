from __future__ import annotations

"""code_review_mini 场景的结构化产物 Schema。

这些 schema 属于具体代码审查场景，不进入 runtime_core。Runtime Core 只负责保存、
校验和交接 ArtifactRecord。
"""

from pydantic import BaseModel, Field


class CodeSnapshot(BaseModel):
    """被审查代码的最小快照。"""

    file_path: str = Field(description="被审查文件路径。")
    language: str = Field(default="python", description="代码语言。")
    content: str = Field(description="代码内容。")
    line_count: int = Field(ge=0, description="代码行数。")


class CodeFinding(BaseModel):
    """单条代码审查发现。"""

    finding_id: str = Field(description="发现 ID，用于后续 patch suggestion 引用。")
    severity: str = Field(description="严重程度：low / medium / high。")
    category: str = Field(description="问题类别，例如 safety、bug、maintainability。")
    message: str = Field(description="问题描述。")
    file_path: str = Field(description="问题所在文件。")
    line_start: int = Field(ge=1, description="起始行。")
    line_end: int = Field(ge=1, description="结束行。")
    evidence: str = Field(default="", description="触发判断的代码片段或证据。")
    recommendation: str = Field(default="", description="修复或处理建议。")


class ReviewReport(BaseModel):
    """代码审查报告。"""

    summary: str = Field(description="审查摘要。")
    findings: list[CodeFinding] = Field(default_factory=list, description="审查发现。")
    risk_level: str = Field(description="整体风险等级：low / medium / high。")
    passed: bool = Field(description="是否通过审查。")
    reviewer: str = Field(default="deterministic", description="审查来源。")


class PatchSuggestion(BaseModel):
    """补丁建议，只描述建议，不直接修改文件。"""

    file_path: str = Field(description="建议修改的文件。")
    finding_refs: list[str] = Field(default_factory=list, description="关联 finding_id。")
    summary: str = Field(description="补丁建议摘要。")
    suggested_changes: list[str] = Field(default_factory=list, description="建议修改点。")
    requires_human_approval: bool = Field(default=True, description="是否需要人工确认。")


DEFAULT_CODE_REVIEW_MINI_SCHEMAS: dict[str, type[BaseModel]] = {
    "CodeSnapshotV1": CodeSnapshot,
    "ReviewReportV1": ReviewReport,
    "PatchSuggestionV1": PatchSuggestion,
}

