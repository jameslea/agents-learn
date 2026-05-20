from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from runtime_core.context.source import ContextSourceType, ContextTrustLevel, ContextVisibility


class ContextCandidate(BaseModel):
    """统一上下文候选模型。

    ContextCandidate 是进入 ContextBuilder 前的统一输入。后续 state、artifact、
    memory、trace、resource、tool description 都可以先适配为 candidate。
    """

    source_type: ContextSourceType = Field(description="候选来源类型。")
    source_id: str = Field(description="候选唯一标识。")
    title: str = Field(description="候选标题。")
    content: str = Field(description="候选正文或摘要。")
    tags: list[str] = Field(default_factory=list, description="候选标签，用于和 step tags 做相关性匹配。")
    visibility: ContextVisibility = Field(default=ContextVisibility.LLM_VISIBLE, description="候选可见性。")
    trust_level: ContextTrustLevel = Field(default=ContextTrustLevel.SYSTEM, description="候选信任等级。")
    sensitive: bool = Field(default=False, description="是否包含敏感内容。")
    artifact_type: str = Field(default="", description="如果候选来自 artifact，这里记录 artifact type。")
    scope: str = Field(default="", description="候选适用范围，主要用于 memory。")
    confidence: float = Field(default=1.0, description="候选置信度，主要用于 memory。")
    validated: bool = Field(default=True, description="候选是否经过验证，主要用于 memory。")
    expires_at: str | None = Field(default=None, description="候选过期时间，UTC ISO 字符串。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="候选扩展元数据。")

class ArtifactCandidate(BaseModel):
    """可供 ContextBuilder 选择的 artifact 摘要候选。

    注意：这里不读取完整 artifact 正文，只提供摘要、类型、路径和标签。
    完整 artifact 后续应由 artifact store 管理。
    """

    artifact_id: str = Field(description="artifact 唯一标识。")
    title: str = Field(description="artifact 标题。")
    summary: str = Field(description="artifact 摘要，进入上下文时使用该字段而不是完整正文。")
    tags: list[str] = Field(default_factory=list, description="artifact 标签，用于相关性筛选。")
    artifact_type: str = Field(default="unknown", description="artifact 类型，例如 evidence_table、draft_report。")
    path: str = Field(default="", description="artifact 存储路径或引用路径。")
    visibility: ContextVisibility = Field(default=ContextVisibility.SUMMARY_ONLY, description="artifact 默认只摘要可见。")
    trust_level: ContextTrustLevel = Field(default=ContextTrustLevel.ARTIFACT, description="artifact 默认信任等级。")
    sensitive: bool = Field(default=False, description="artifact 摘要是否包含敏感内容。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="artifact 扩展元数据。")

class MemoryCandidate(BaseModel):
    """可供 ContextBuilder 选择的 memory 摘要候选。

    当前保留它是为了兼容阶段 1 demo 和测试。阶段 2 起，正式记忆模型是
    `runtime_core.memory.MemoryRecord`。
    """

    memory_id: str = Field(description="memory 唯一标识。")
    content: str = Field(description="memory 摘要内容。")
    scope: str = Field(default="global", description="适用范围，例如 global、task_type、task_id。")
    tags: list[str] = Field(default_factory=list, description="memory 标签，用于和 step tags 匹配。")
    confidence: float = Field(default=1.0, description="memory 置信度，低于策略阈值会被排除。")
    validated: bool = Field(default=True, description="memory 是否经过验证，未验证会被排除。")
    expires_at: str | None = Field(default=None, description="memory 过期时间，过期会被排除。")
    visibility: ContextVisibility = Field(default=ContextVisibility.SUMMARY_ONLY, description="memory 默认只摘要可见。")
    trust_level: ContextTrustLevel = Field(default=ContextTrustLevel.MEMORY, description="memory 默认信任等级。")
    sensitive: bool = Field(default=False, description="memory 是否包含敏感内容。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="memory 扩展元数据。")
