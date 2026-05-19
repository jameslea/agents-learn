from __future__ import annotations

"""Runtime Core 的结构化产物模型。

Artifact 保存任务产生的可交接、可验证产物。它和 RuntimeState 的区别是：
State 记录“执行到哪里”，Artifact 记录“产出了什么”；它和 Memory 的区别是：
Memory 保存可复用经验，Artifact 保存具体任务产物。

主要类与关系：
- ArtifactRecord：一条可被引用和交接的结构化产物记录。

典型关系：
ArtifactRecord -> ContextCandidate -> ContextBuilder
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactRecord(BaseModel):
    """可验证、可交接的结构化产物记录。"""

    artifact_id: str = Field(description="artifact 唯一标识。")
    artifact_type: str = Field(description="artifact 类型，例如 evidence_table、draft_report。")
    title: str = Field(description="artifact 标题。")
    summary: str = Field(description="artifact 摘要，进入上下文时使用摘要而不是完整正文。")
    path: str = Field(default="", description="artifact 存储路径或引用路径。")
    schema_name: str = Field(default="", description="产物 schema 名称，用于后续验证和交接。")
    producer_step_id: str = Field(default="", description="生成该 artifact 的 step id。")
    tags: list[str] = Field(default_factory=list, description="用于和当前 step tags 匹配。")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="结构化产物内容。ContextBuilder 默认不读取该字段。",
    )
    validated: bool = Field(default=True, description="artifact 是否通过 schema 或人工验证。")
    created_at: str = Field(default_factory=utc_now, description="创建时间，UTC ISO 格式。")
    sensitive: bool = Field(default=False, description="摘要或引用信息是否包含敏感内容。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据。")

    def to_candidate(self):
        """转换为 ContextBuilder 可消费的 ContextCandidate。

        注意：转换时只暴露 summary、path、schema 等引用信息，不暴露 payload。
        """
        from runtime_core.context import ContextCandidate, ContextSourceType, ContextTrustLevel, ContextVisibility

        return ContextCandidate(
            source_type=ContextSourceType.ARTIFACT_REF,
            source_id=self.artifact_id,
            title=f"Artifact: {self.title}",
            content=self.summary,
            tags=self.tags,
            visibility=ContextVisibility.SUMMARY_ONLY,
            trust_level=ContextTrustLevel.ARTIFACT,
            sensitive=self.sensitive,
            artifact_type=self.artifact_type,
            metadata={
                "path": self.path,
                "schema_name": self.schema_name,
                "producer_step_id": self.producer_step_id,
                "validated": self.validated,
                "created_at": self.created_at,
                **self.metadata,
            },
        )
