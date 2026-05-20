from __future__ import annotations

from pydantic import BaseModel, Field

from runtime_core.memory.record import MemoryRecord


class MemoryQuery(BaseModel):
    """记忆检索请求。"""

    scopes: list[str] = Field(default_factory=lambda: ["global"], description="允许检索的 scope。")
    tags: list[str] = Field(default_factory=list, description="当前 step 或任务标签。")
    min_confidence: float = Field(default=0.6, description="最低置信度。")
    include_unvalidated: bool = Field(default=False, description="是否允许未验证记忆进入检索结果。")
    include_expired: bool = Field(default=False, description="是否允许过期记忆进入检索结果。")
    include_sensitive: bool = Field(default=False, description="是否允许敏感记忆进入检索结果。")
    include_inactive: bool = Field(default=False, description="是否允许 invalidated / archived 记忆进入检索结果。")
    limit: int = Field(default=5, description="最多返回多少条记忆。")

class MemorySearchResult(BaseModel):
    """带分数和原因的记忆检索结果。"""

    record: MemoryRecord = Field(description="匹配的记忆记录。")
    score: float = Field(description="简单相关性分数。")
    reason: str = Field(description="进入结果的原因。")
