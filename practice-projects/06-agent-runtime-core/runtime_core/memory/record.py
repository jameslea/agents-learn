from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class MemoryStatus(str, Enum):
    """记忆状态。"""

    ACTIVE = "active"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"

class MemoryRecord(BaseModel):
    """跨任务可复用的记忆记录。

    MemoryRecord 是正式 memory 模型。阶段 2 只验证边界和筛选元数据，
    不实现向量检索、自动抽取或复杂排序。
    """

    memory_id: str = Field(description="memory 唯一标识。")
    content: str = Field(description="可复用经验、偏好或规则的摘要内容。")
    scope: str = Field(default="global", description="适用范围，例如 global、task_type、task_id。")
    tags: list[str] = Field(default_factory=list, description="用于和当前 step tags 匹配。")
    confidence: float = Field(default=1.0, description="记忆置信度，低于策略阈值不进入上下文。")
    validated: bool = Field(default=True, description="是否经过验证。未验证记忆默认不进入上下文。")
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE, description="记忆状态。非 active 不进入默认检索。")
    version: int = Field(default=1, description="记忆版本。更新或替换时递增。")
    supersedes: list[str] = Field(default_factory=list, description="该记忆替代的旧 memory id。")
    source: str = Field(default="", description="记忆来源，例如 user、human_review、previous_task。")
    created_at: str = Field(default_factory=utc_now, description="创建时间，UTC ISO 格式。")
    updated_at: str = Field(default_factory=utc_now, description="更新时间，UTC ISO 格式。")
    expires_at: str | None = Field(default=None, description="过期时间。过期记忆不应进入上下文。")
    sensitive: bool = Field(default=False, description="是否包含敏感信息。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据。")

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """判断记忆是否过期。非法时间格式按过期处理。"""
        if not self.expires_at:
            return False
        current = now or datetime.now(timezone.utc)
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < current

    def to_candidate(self):
        """转换为 ContextBuilder 可消费的 ContextCandidate。

        这里使用局部 import，避免 memory 模块和 context 模块在顶层互相依赖。
        """
        from runtime_core.context import ContextCandidate, ContextSourceType, ContextTrustLevel, ContextVisibility

        return ContextCandidate(
            source_type=ContextSourceType.MEMORY,
            source_id=self.memory_id,
            title=f"Memory: {self.memory_id}",
            content=self.content,
            tags=self.tags,
            visibility=ContextVisibility.SUMMARY_ONLY,
            trust_level=ContextTrustLevel.MEMORY,
            sensitive=self.sensitive,
            scope=self.scope,
            confidence=self.confidence,
            validated=self.validated,
            expires_at=self.expires_at,
            metadata={
                "source": self.source,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                **self.metadata,
            },
        )
