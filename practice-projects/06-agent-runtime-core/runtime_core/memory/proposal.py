from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from runtime_core.memory.record import MemoryRecord


class MemoryWriteAction(str, Enum):
    """记忆写入决策动作。"""

    REJECT = "reject"
    PROPOSE = "propose"
    ACTIVATE = "activate"

class MemoryWriteSource(str, Enum):
    """候选记忆来源类型。"""

    USER_PREFERENCE = "user_preference"
    HUMAN_REVIEW = "human_review"
    TASK_RETROSPECTIVE = "task_retrospective"
    FAILURE_LESSON = "failure_lesson"
    AGENT_INFERENCE = "agent_inference"
    EXTERNAL_CONTENT = "external_content"

class MemoryWriteProposal(BaseModel):
    """候选记忆写入请求。

    Proposal 表示“这条信息可能值得长期记住”。它还不是正式记忆，
    必须经过 MemoryWriteGate 判断后才能进入 MemoryStore。
    """

    memory_id: str = Field(description="候选记忆 ID。")
    content: str = Field(description="候选记忆内容。")
    source: MemoryWriteSource = Field(description="候选记忆来源。")
    scope: str = Field(default="global", description="候选记忆适用范围。")
    tags: list[str] = Field(default_factory=list, description="候选记忆标签。")
    confidence: float = Field(default=0.5, description="候选记忆置信度。")
    reusable: bool = Field(default=True, description="是否具备跨任务复用价值。")
    sensitive: bool = Field(default=False, description="是否包含敏感信息。")
    evidence: str = Field(default="", description="写入依据，例如用户原话、人工 review 或失败复盘摘要。")
    from_step_id: str = Field(default="", description="候选记忆来源 step id。")
    from_artifact_id: str = Field(default="", description="候选记忆来源 artifact id。")
    expires_at: str | None = Field(default=None, description="候选记忆过期时间。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据。")

class MemoryWritePolicy(BaseModel):
    """记忆写入门控策略。"""

    min_confidence: float = Field(default=0.6, description="允许写入的最低置信度。")
    allow_sensitive: bool = Field(default=False, description="是否允许写入敏感记忆。")
    require_tags: bool = Field(default=True, description="是否要求候选记忆必须带 tag。")
    require_evidence: bool = Field(default=True, description="是否要求候选记忆必须说明写入依据。")
    activate_sources: list[MemoryWriteSource] = Field(
        default_factory=lambda: [MemoryWriteSource.USER_PREFERENCE, MemoryWriteSource.HUMAN_REVIEW],
        description="可直接写为 active memory 的来源。",
    )
    propose_sources: list[MemoryWriteSource] = Field(
        default_factory=lambda: [
            MemoryWriteSource.TASK_RETROSPECTIVE,
            MemoryWriteSource.FAILURE_LESSON,
            MemoryWriteSource.AGENT_INFERENCE,
        ],
        description="只能先进入 proposed memory 的来源。",
    )
    reject_sources: list[MemoryWriteSource] = Field(
        default_factory=lambda: [MemoryWriteSource.EXTERNAL_CONTENT],
        description="默认拒绝直接写入的来源。",
    )

class MemoryWriteDecision(BaseModel):
    """记忆写入门控结果。"""

    action: MemoryWriteAction = Field(description="写入动作。")
    reasons: list[str] = Field(default_factory=list, description="决策原因。")
    record: MemoryRecord | None = Field(default=None, description="允许写入时生成的记忆记录。")
