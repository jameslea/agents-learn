from __future__ import annotations

from runtime_core.artifact import ArtifactRecord
from runtime_core.context.bundle import ContextBundle, ContextItem
from runtime_core.context.candidate import ArtifactCandidate, ContextCandidate, MemoryCandidate
from runtime_core.context.policy import ContextPolicy
from runtime_core.context.rules.budget import apply_context_budget, truncate
from runtime_core.context.rules.relevance import _is_expired, _normalize_tags, score_by_tags
from runtime_core.context.rules.required import find_missing_required_context
from runtime_core.context.selection import ContextMetrics, ContextSelection
from runtime_core.context.source import ContextSourceType, ContextTrustLevel, ContextVisibility
from runtime_core.task import TaskContract
from runtime_core.memory import MemoryRecord
from runtime_core.task import RuntimeState, StepExecution, StepStatus


class ContextBuilder:
    """从 state、artifact 摘要和 memory 中构造有边界的 ContextBundle。"""

    def __init__(
        self,
        *,
        max_recent_steps: int = 3,
        max_item_chars: int = 500,
        max_context_chars: int = 3000,
        min_memory_confidence: float = 0.6,
        policy: ContextPolicy | None = None,
    ) -> None:
        self.policy = policy or ContextPolicy(
            max_recent_steps=max_recent_steps,
            max_item_chars=max_item_chars,
            max_context_chars=max_context_chars,
            min_memory_confidence=min_memory_confidence,
        )

    def build(
        self,
        *,
        contract: TaskContract,
        state: RuntimeState,
        step_id: str,
        current_step: str,
        step_tags: list[str] | None = None,
        artifacts: list[ArtifactCandidate | ArtifactRecord] | None = None,
        memories: list[MemoryCandidate | MemoryRecord] | None = None,
        candidates: list[ContextCandidate] | None = None,
        trace_summary: str = "",
        policy: ContextPolicy | None = None,
    ) -> ContextBundle:
        """为单个 step 构造上下文，并记录可解释的选择日志。"""
        active_policy = policy or self.policy
        tags = _normalize_tags(step_tags or [])
        items: list[ContextItem] = []

        # 任务目标和当前 step 是硬约束：它们不参与相关性筛选，但要进入
        # selection_log，方便后续 trace 复盘“这次上下文服务于什么目标”。
        selection_log: list[ContextSelection] = [
            ContextSelection(
                source_type=ContextSourceType.GOAL,
                source_id=contract.task_id,
                included=True,
                reason="任务目标是当前 step 的硬约束，始终进入上下文。",
                score=1.0,
                trust_level=ContextTrustLevel.SYSTEM,
            ),
            ContextSelection(
                source_type=ContextSourceType.CURRENT_STEP,
                source_id=step_id,
                included=True,
                reason="当前 step 是本次上下文构造的直接工作目标，始终进入上下文。",
                score=1.0,
                tags=tags,
                trust_level=ContextTrustLevel.SYSTEM,
            ),
        ]

        # 历史 step 只保留摘要，并且只取最近少量已完成记录。
        # 这样可以让模型看到执行进展，又不会把完整历史上下文不断累积进去。
        for step in self._recent_step_summaries(state, current_step_id=step_id, policy=active_policy):
            content = self._summarize_step(step)
            items.append(
                ContextItem(
                    source_type=ContextSourceType.STEP_SUMMARY,
                    source_id=step.step_id,
                    title=f"Recent Step: {step.name}",
                    content=truncate(content, policy=active_policy),
                    visibility=ContextVisibility.SUMMARY_ONLY,
                    trust_level=ContextTrustLevel.SYSTEM,
                    metadata={"status": step.status.value},
                )
            )
            selection_log.append(
                ContextSelection(
                    source_type=ContextSourceType.STEP_SUMMARY,
                    source_id=step.step_id,
                    included=True,
                    reason=f"保留最近 {active_policy.max_recent_steps} 个已完成 step 摘要，避免塞入完整历史。",
                    score=0.8,
                    visibility=ContextVisibility.SUMMARY_ONLY,
                    trust_level=ContextTrustLevel.SYSTEM,
                )
            )

        # artifact、memory、trace summary 和外部传入 candidate 会先统一转换为
        # ContextCandidate，再走同一套 visibility / sensitive / trust / relevance 策略。
        for candidate in self._collect_candidates(
            contract=contract,
            artifacts=artifacts or [],
            memories=memories or [],
            candidates=candidates or [],
            trace_summary=trace_summary,
            policy=active_policy,
        ):
            included, reason, score = self._select_candidate(
                candidate,
                contract=contract,
                step_tags=tags,
                policy=active_policy,
            )
            if included:
                items.append(
                    ContextItem(
                        source_type=candidate.source_type,
                        source_id=candidate.source_id,
                        title=candidate.title,
                        content=truncate(candidate.content, policy=active_policy),
                        visibility=candidate.visibility,
                        trust_level=candidate.trust_level,
                        sensitive=candidate.sensitive,
                        metadata={
                            "tags": candidate.tags,
                            "artifact_type": candidate.artifact_type,
                            "scope": candidate.scope,
                            "confidence": candidate.confidence,
                            "validated": candidate.validated,
                            **candidate.metadata,
                        },
                    )
                )
            selection_log.append(
                ContextSelection(
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    included=included,
                    reason=reason,
                    score=score,
                    tags=candidate.tags,
                    visibility=candidate.visibility,
                    trust_level=candidate.trust_level,
                    sensitive=candidate.sensitive,
                )
            )

        # 最后一层再执行总预算裁剪。这样 selection_log 可以记录“原本通过筛选，
        # 但因为预算不足被移除”的情况，而不是静默丢弃。
        bounded_items = apply_context_budget(items, selection_log, policy=active_policy)
        missing_required_context = find_missing_required_context(bounded_items, active_policy)
        estimated_chars = len(contract.goal) + len(current_step) + sum(len(item.content) for item in bounded_items)
        ready = not missing_required_context

        # Metrics 是上下文治理的观测面：它不影响选择结果，但会帮助测试、
        # 调试和后续 trace 复盘。
        metrics = self._build_metrics(
            items=bounded_items,
            selection_log=selection_log,
            total_chars=estimated_chars,
            policy=active_policy,
            missing_required_count=len(missing_required_context),
        )
        return ContextBundle(
            task_id=contract.task_id,
            task_type=contract.task_type.value,
            step_id=step_id,
            goal=contract.goal,
            current_step=current_step,
            items=bounded_items,
            selection_log=selection_log,
            metrics=metrics,
            estimated_chars=estimated_chars,
            excluded_count=sum(1 for item in selection_log if not item.included),
            ready=ready,
            missing_required_context=missing_required_context,
            blocked_reason="缺少 required context，当前 step 不应继续执行。" if not ready else "",
        )

    def _recent_step_summaries(
        self,
        state: RuntimeState,
        *,
        current_step_id: str,
        policy: ContextPolicy,
    ) -> list[StepExecution]:
        """选择最近已完成 step，排除当前正在构造上下文的 step。"""
        completed = [
            step
            for step in state.steps
            if step.step_id != current_step_id and step.status in {StepStatus.PASSED, StepStatus.FAILED}
        ]
        return completed[-policy.max_recent_steps :]

    def _summarize_step(self, step: StepExecution) -> str:
        """把 StepExecution 压缩为适合进入上下文的短摘要。"""
        parts = [f"step_id={step.step_id}", f"status={step.status.value}"]
        if step.outputs_summary:
            parts.append(f"outputs={step.outputs_summary}")
        if step.error:
            parts.append(f"error={step.error}")
        return "; ".join(parts)

    def _select_memory(
        self,
        memory: MemoryCandidate,
        *,
        contract: TaskContract,
        step_tags: list[str],
        policy: ContextPolicy,
    ) -> tuple[bool, str, float]:
        """memory 的专用筛选规则，重点防止陈旧或低置信度记忆污染上下文。"""
        if not memory.validated:
            return False, "memory 未验证，暂不进入上下文。", 0.0
        if memory.confidence < policy.min_memory_confidence:
            return False, "memory 置信度低于阈值，避免污染上下文。", memory.confidence
        if _is_expired(memory.expires_at):
            return False, "memory 已过期，避免使用陈旧信息。", 0.0
        if memory.scope not in {"global", contract.task_type.value, contract.task_id}:
            return False, "memory scope 与当前任务不匹配。", 0.0
        score = score_by_tags(memory.tags, step_tags)
        if score <= 0:
            return False, "memory tag 与当前 step 无关。", 0.0
        return True, "memory 通过 scope、tag、置信度和有效期筛选。", score

    def _collect_candidates(
        self,
        *,
        contract: TaskContract,
        artifacts: list[ArtifactCandidate | ArtifactRecord],
        memories: list[MemoryCandidate | MemoryRecord],
        candidates: list[ContextCandidate],
        trace_summary: str,
        policy: ContextPolicy,
    ) -> list[ContextCandidate]:
        """把不同来源统一适配成 ContextCandidate。

        build() 后续只处理 candidate，因此新增来源时优先扩展这里或外部
        adapter，而不是把来源特定逻辑散落到选择流程里。
        """
        collected = list(candidates)

        # Artifact 默认只暴露摘要和引用元数据，不在 ContextBuilder 阶段读取完整正文。
        for artifact in artifacts:
            if isinstance(artifact, ArtifactRecord):
                collected.append(artifact.to_candidate())
                continue
            collected.append(
                ContextCandidate(
                    source_type=ContextSourceType.ARTIFACT_REF,
                    source_id=artifact.artifact_id,
                    title=f"Artifact: {artifact.title}",
                    content=artifact.summary,
                    tags=artifact.tags,
                    visibility=artifact.visibility,
                    trust_level=artifact.trust_level,
                    sensitive=artifact.sensitive,
                    artifact_type=artifact.artifact_type,
                    metadata={"path": artifact.path, **artifact.metadata},
                )
            )

        # MemoryRecord 是阶段 2 的正式模型；MemoryCandidate 仅用于兼容阶段 1。
        # 转换为 ContextCandidate 后仍统一走 _select_memory() 的治理规则。
        for memory in memories:
            if isinstance(memory, MemoryRecord):
                collected.append(memory.to_candidate())
                continue
            collected.append(
                ContextCandidate(
                    source_type=ContextSourceType.MEMORY,
                    source_id=memory.memory_id,
                    title=f"Memory: {memory.memory_id}",
                    content=memory.content,
                    tags=memory.tags,
                    visibility=memory.visibility,
                    trust_level=memory.trust_level,
                    sensitive=memory.sensitive,
                    scope=memory.scope,
                    confidence=memory.confidence,
                    validated=memory.validated,
                    expires_at=memory.expires_at,
                    metadata=memory.metadata,
                )
            )

        # Trace 只允许摘要进入上下文，避免原始 trace 过长、过噪或携带敏感工具输出。
        if policy.include_trace_summary and trace_summary.strip():
            collected.append(
                ContextCandidate(
                    source_type=ContextSourceType.TRACE_SUMMARY,
                    source_id=f"{contract.task_id}:trace_summary",
                    title="Trace Summary",
                    content=trace_summary,
                    visibility=ContextVisibility.SUMMARY_ONLY,
                    trust_level=ContextTrustLevel.SYSTEM,
                    metadata={"raw_trace_included": False},
                )
            )
        return collected

    def _select_candidate(
        self,
        candidate: ContextCandidate,
        *,
        contract: TaskContract,
        step_tags: list[str],
        policy: ContextPolicy,
    ) -> tuple[bool, str, float]:
        """对统一 candidate 执行可见性、安全性和相关性筛选。"""
        # 第一层是硬性安全边界：Runtime-only、敏感信息、不可信来源默认不进模型。
        if candidate.visibility == ContextVisibility.RUNTIME_ONLY:
            return False, "candidate 仅 Runtime 可见，不进入模型上下文。", 0.0
        if candidate.sensitive and policy.exclude_sensitive:
            return False, "candidate 标记为 sensitive，策略禁止进入模型上下文。", 0.0
        if (
            candidate.trust_level == ContextTrustLevel.UNTRUSTED
            and not policy.allow_untrusted_external_context
        ):
            return False, "candidate 来源不可信，策略禁止进入模型上下文。", 0.0

        # Memory 的风险主要来自“过期、未验证、低置信度、scope 不匹配”，
        # 因此走独立规则，而不是只按 tag 命中就进入上下文。
        if candidate.source_type == ContextSourceType.MEMORY:
            memory = MemoryCandidate(
                memory_id=candidate.source_id,
                content=candidate.content,
                scope=candidate.scope or "global",
                tags=candidate.tags,
                confidence=candidate.confidence,
                validated=candidate.validated,
                expires_at=candidate.expires_at,
                visibility=candidate.visibility,
                trust_level=candidate.trust_level,
                sensitive=candidate.sensitive,
                metadata=candidate.metadata,
            )
            return self._select_memory(memory, contract=contract, step_tags=step_tags, policy=policy)

        # Trace summary 是运行过程摘要，当前实现不要求 tag 命中。
        if candidate.source_type == ContextSourceType.TRACE_SUMMARY:
            return True, "只加入 trace 摘要，不加入原始 trace，降低噪音和泄露风险。", 0.5

        # 其他候选目前用 tag overlap 做最小相关性判断。
        # 后续可以替换为检索分数、规则优先级或 LLM rerank。
        score = score_by_tags(candidate.tags, step_tags)
        if score <= 0:
            return False, "candidate tag 与当前 step 无关，避免污染上下文。", 0.0
        if candidate.source_type == ContextSourceType.ARTIFACT_REF:
            return True, "artifact tag 与当前 step tag 匹配，只引用摘要和路径。", score
        return True, "candidate tag 与当前 step tag 匹配。", score

    def _build_metrics(
        self,
        *,
        items: list[ContextItem],
        selection_log: list[ContextSelection],
        total_chars: int,
        policy: ContextPolicy,
        missing_required_count: int,
    ) -> ContextMetrics:
        """基于最终上下文和选择日志生成观测指标。"""
        breakdown: dict[str, int] = {}
        for item in items:
            key = item.source_type.value
            breakdown[key] = breakdown.get(key, 0) + 1
        return ContextMetrics(
            total_chars=total_chars,
            item_count=len(items),
            included_count=sum(1 for item in selection_log if item.included),
            excluded_count=sum(1 for item in selection_log if not item.included),
            source_type_breakdown=breakdown,
            budget_used_ratio=round(total_chars / policy.max_context_chars, 4)
            if policy.max_context_chars
            else 0.0,
            sensitive_excluded_count=sum(
                1 for item in selection_log if not item.included and item.sensitive
            ),
            untrusted_excluded_count=sum(
                1
                for item in selection_log
                if not item.included and item.trust_level == ContextTrustLevel.UNTRUSTED
            ),
            missing_required_count=missing_required_count,
        )
