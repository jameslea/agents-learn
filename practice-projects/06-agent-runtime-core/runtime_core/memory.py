from __future__ import annotations

"""Runtime Core 的长期记忆模型。

Memory 保存跨任务可复用的经验、偏好或规则。它不记录当前任务进度，
也不保存结构化产物正文；这些分别属于 RuntimeState 和 ArtifactRecord。

主要类与关系：
- MemoryRecord：一条可被 ContextBuilder 引用的长期记忆。
- MemoryQuery：一次记忆检索请求。
- MemorySearchResult：一条带分数和原因的检索结果。
- MemoryWriteProposal：一条候选记忆写入请求。
- MemoryWritePolicy：记忆写入门控策略。
- MemoryWriteDecision：记忆写入门控结果。
- MemoryWriteGate：判断候选信息是否应该进入记忆系统。
- MemoryStore：最小内存记忆库，负责写入、验证、检索和失效。

典型关系：
MemoryWriteProposal -> MemoryWriteGate -> MemoryStore -> ContextBuilder
"""

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


class MemoryWriteGate:
    """最小记忆写入门控。

    它回答“什么时候应该写入 memory”。当前只做规则判断，不做 LLM 抽取。
    通过门控后，候选内容要么被拒绝，要么成为待验证记忆，要么直接成为
    active memory。
    """

    def __init__(self, policy: MemoryWritePolicy | None = None) -> None:
        self.policy = policy or MemoryWritePolicy()

    def decide(self, proposal: MemoryWriteProposal) -> MemoryWriteDecision:
        """根据策略判断候选信息是否应写入记忆。"""
        reject_reasons = self._reject_reasons(proposal)
        if reject_reasons:
            return MemoryWriteDecision(action=MemoryWriteAction.REJECT, reasons=reject_reasons)

        if proposal.source in self.policy.activate_sources:
            return MemoryWriteDecision(
                action=MemoryWriteAction.ACTIVATE,
                reasons=["来源可信，可直接写入 active memory。"],
                record=self._to_record(proposal, validated=True),
            )
        if proposal.source in self.policy.propose_sources:
            return MemoryWriteDecision(
                action=MemoryWriteAction.PROPOSE,
                reasons=["来源需要验证，先写入 proposed memory。"],
                record=self._to_record(proposal, validated=False),
            )
        return MemoryWriteDecision(
            action=MemoryWriteAction.REJECT,
            reasons=[f"来源不在允许写入范围内: {proposal.source.value}"],
        )

    def apply(self, proposal: MemoryWriteProposal, store: "MemoryStore") -> MemoryWriteDecision:
        """执行写入门控，并在允许时写入 MemoryStore。"""
        decision = self.decide(proposal)
        if decision.record is None:
            return decision
        store.add(decision.record)
        return decision

    def _reject_reasons(self, proposal: MemoryWriteProposal) -> list[str]:
        reasons: list[str] = []
        if proposal.source in self.policy.reject_sources:
            reasons.append("来源默认不允许直接写入 memory。")
        if not proposal.reusable:
            reasons.append("候选信息不具备跨任务复用价值。")
        if not proposal.content.strip():
            reasons.append("候选记忆内容为空。")
        if proposal.confidence < self.policy.min_confidence:
            reasons.append("候选记忆置信度低于写入阈值。")
        if proposal.sensitive and not self.policy.allow_sensitive:
            reasons.append("候选记忆包含敏感信息。")
        if self.policy.require_tags and not _normalize_tags(proposal.tags):
            reasons.append("候选记忆缺少 tag，无法治理和检索。")
        if self.policy.require_evidence and not proposal.evidence.strip():
            reasons.append("候选记忆缺少写入依据。")
        return reasons

    def _to_record(self, proposal: MemoryWriteProposal, *, validated: bool) -> MemoryRecord:
        return MemoryRecord(
            memory_id=proposal.memory_id,
            content=proposal.content,
            scope=proposal.scope,
            tags=proposal.tags,
            confidence=proposal.confidence,
            validated=validated,
            source=proposal.source.value,
            expires_at=proposal.expires_at,
            sensitive=proposal.sensitive,
            metadata={
                "write_source": proposal.source.value,
                "write_evidence": proposal.evidence,
                "from_step_id": proposal.from_step_id,
                "from_artifact_id": proposal.from_artifact_id,
                **proposal.metadata,
            },
        )


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


class MemoryStore:
    """最小内存记忆库。

    它只覆盖记忆系统的主要机制：写入、验证、检索、排序、失效。
    本阶段不负责持久化、向量检索、多用户隔离或自动记忆抽取。
    所有记录保存在当前 Python 进程内，进程退出后会丢失。
    """

    def __init__(self, records: list[MemoryRecord] | None = None) -> None:
        # 阶段 2 使用内存字典作为最小 store，重点验证记忆生命周期和检索机制。
        # 后续如果需要持久化，可以在不改变 MemoryRecord 的前提下替换为
        # JSON / SQLite / database-backed store。
        self._records: dict[str, MemoryRecord] = {}
        for record in records or []:
            self.add(record)

    def add(self, record: MemoryRecord, *, overwrite: bool = False) -> MemoryRecord:
        """写入一条记忆。默认不允许覆盖同 ID 记录。"""
        if record.memory_id in self._records and not overwrite:
            raise KeyError(f"Memory already exists: {record.memory_id}")
        self._records[record.memory_id] = record
        return record

    def propose(
        self,
        *,
        memory_id: str,
        content: str,
        source: str,
        scope: str = "global",
        tags: list[str] | None = None,
        confidence: float = 0.5,
        sensitive: bool = False,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """提出一条待验证记忆。

        propose 用于模拟 Agent 从任务中发现“可能可复用”的经验。它默认
        `validated=False`，避免未审核内容直接污染上下文。
        """
        return self.add(
            MemoryRecord(
                memory_id=memory_id,
                content=content,
                scope=scope,
                tags=tags or [],
                confidence=confidence,
                validated=False,
                source=source,
                sensitive=sensitive,
                expires_at=expires_at,
                metadata=metadata or {},
            )
        )

    def get(self, memory_id: str) -> MemoryRecord:
        """读取一条记忆。"""
        try:
            return self._records[memory_id]
        except KeyError as exc:
            raise KeyError(f"Memory not found: {memory_id}") from exc

    def validate(
        self,
        memory_id: str,
        *,
        confidence: float | None = None,
        source: str | None = None,
    ) -> MemoryRecord:
        """将一条记忆标记为已验证。"""
        record = self.get(memory_id)
        record.validated = True
        if confidence is not None:
            record.confidence = confidence
        if source is not None:
            record.source = source
        record.updated_at = utc_now()
        return record

    def invalidate(self, memory_id: str, *, reason: str) -> MemoryRecord:
        """将一条记忆失效。失效记忆默认不会进入检索结果。"""
        record = self.get(memory_id)
        record.status = MemoryStatus.INVALIDATED
        record.metadata["invalidated_reason"] = reason
        record.updated_at = utc_now()
        return record

    def replace(
        self,
        *,
        old_memory_id: str,
        new_record: MemoryRecord,
    ) -> MemoryRecord:
        """用新记忆替代旧记忆，并保留替代关系。"""
        old_record = self.invalidate(old_memory_id, reason=f"replaced_by:{new_record.memory_id}")
        new_record.version = old_record.version + 1
        if old_memory_id not in new_record.supersedes:
            new_record.supersedes.append(old_memory_id)
        new_record.updated_at = utc_now()
        return self.add(new_record)

    def list_records(self, *, include_inactive: bool = False) -> list[MemoryRecord]:
        """列出记忆。默认只返回 active 记忆。"""
        records = list(self._records.values())
        if include_inactive:
            return records
        return [record for record in records if record.status == MemoryStatus.ACTIVE]

    def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """按 scope、tag、置信度、验证状态和有效期检索记忆。"""
        results: list[MemorySearchResult] = []
        query_tags = _normalize_tags(query.tags)
        query_scopes = set(query.scopes)

        for record in self._records.values():
            # 先做治理过滤，再算相关性分数。这样未验证、过期、敏感、
            # inactive 或 scope 不匹配的记忆不会因为 tag 命中而进入上下文。
            included, reason = self._can_return(record, query=query, query_scopes=query_scopes)
            if not included:
                continue
            score = _score_memory(record, query_tags=query_tags)
            if query_tags and score <= 0:
                continue
            results.append(MemorySearchResult(record=record, score=score, reason=reason))

        results.sort(key=lambda item: (item.score, item.record.updated_at), reverse=True)
        return results[: query.limit]

    def _can_return(
        self,
        record: MemoryRecord,
        *,
        query: MemoryQuery,
        query_scopes: set[str],
    ) -> tuple[bool, str]:
        if record.status != MemoryStatus.ACTIVE and not query.include_inactive:
            return False, "memory 非 active 状态。"
        if record.scope not in query_scopes:
            return False, "memory scope 不匹配。"
        if record.sensitive and not query.include_sensitive:
            return False, "memory 标记为 sensitive。"
        if not record.validated and not query.include_unvalidated:
            return False, "memory 未验证。"
        if record.confidence < query.min_confidence:
            return False, "memory 置信度低于检索阈值。"
        if record.is_expired() and not query.include_expired:
            return False, "memory 已过期。"
        return True, "memory 通过 scope、tag、验证状态、置信度和有效期检索。"


def _normalize_tags(tags: list[str]) -> set[str]:
    return {tag.strip().lower() for tag in tags if tag.strip()}


def _score_memory(record: MemoryRecord, *, query_tags: set[str]) -> float:
    if not query_tags:
        return record.confidence
    record_tags = _normalize_tags(record.tags)
    overlap = record_tags & query_tags
    if not overlap:
        return 0.0
    tag_score = len(overlap) / max(len(query_tags), 1)
    return round(min(1.0, 0.5 * record.confidence + 0.5 * tag_score), 4)
