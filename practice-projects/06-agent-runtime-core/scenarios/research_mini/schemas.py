from __future__ import annotations

"""阶段 4 使用的具体 Schema Artifact 定义。

这些类不是通用 registry，而是最小 handoff 场景中的结构化接口：
Research step 产出 EvidenceTable，Writer step 消费它并产出 DraftReport，
Reviewer step 再消费 DraftReport 产出 ReviewResult。
"""

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """证据表中的单条证据。"""

    evidence_id: str = Field(description="证据 ID，用于后续报告引用。")
    claim: str = Field(description="该证据支持的主张。")
    source: str = Field(description="证据来源，可以是 URL、文件路径或人工说明。")
    confidence: float = Field(ge=0, le=1, description="证据可信度，范围 0-1。")
    notes: str = Field(default="", description="补充说明。")


class EvidenceTable(BaseModel):
    """Research step 产出的证据表。"""

    topic: str = Field(description="证据表对应的研究主题。")
    rows: list[EvidenceItem] = Field(min_length=1, description="至少包含一条证据。")


class DraftSection(BaseModel):
    """报告草稿中的一个章节。"""

    heading: str = Field(description="章节标题。")
    content: str = Field(description="章节正文。")
    evidence_refs: list[str] = Field(default_factory=list, description="本章节引用的 evidence_id。")


class DraftReport(BaseModel):
    """Writer step 根据 EvidenceTable 生成的报告草稿。"""

    title: str = Field(description="报告标题。")
    evidence_artifact_id: str = Field(description="来源 EvidenceTable artifact id。")
    sections: list[DraftSection] = Field(min_length=1, description="报告章节。")


class ReviewIssue(BaseModel):
    """Reviewer step 发现的问题。"""

    severity: str = Field(description="问题严重程度，例如 low、medium、high。")
    message: str = Field(description="问题描述。")
    evidence_ref: str = Field(default="", description="关联 evidence_id，可为空。")


class ReviewResult(BaseModel):
    """Reviewer step 对 DraftReport 的审查结果。"""

    score: int = Field(ge=0, le=100, description="审查分数，范围 0-100。")
    issues: list[ReviewIssue] = Field(default_factory=list, description="发现的问题。")
    required_changes: list[str] = Field(default_factory=list, description="必须修改的内容。")
    passed: bool = Field(description="是否通过审查。")


DEFAULT_RESEARCH_MINI_SCHEMAS: dict[str, type[BaseModel]] = {
    "EvidenceTableV1": EvidenceTable,
    "DraftReportV1": DraftReport,
    "ReviewResultV1": ReviewResult,
}
