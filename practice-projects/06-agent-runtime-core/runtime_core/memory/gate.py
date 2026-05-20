from __future__ import annotations

from runtime_core.memory.proposal import (
    MemoryWriteAction,
    MemoryWriteDecision,
    MemoryWritePolicy,
    MemoryWriteProposal,
)
from runtime_core.memory.record import MemoryRecord
from runtime_core.memory.rules.scoring import _normalize_tags


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
