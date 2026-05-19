from __future__ import annotations

"""Context Builder 最小实现。

Agent Runtime 中的 Context Builder 负责为“当前 step”组装工作视图。
它不等同于聊天历史拼接，也不应把完整 trace、完整文件或所有 memory
无差别塞进模型上下文。它要回答三个问题：

1. 当前 step 必须知道什么。
2. 哪些历史信息、artifact 和 memory 与当前 step 有关。
3. 哪些信息被排除，以及排除原因是什么。

主要类与关系：
- ContextSourceType：进入上下文的信息来源类型。
- ContextVisibility：候选信息的可见性，区分可发给模型和仅 Runtime 可见。
- ContextTrustLevel：候选信息的信任等级，用于拦截外部不可信内容。
- ContextItem：最终进入 ContextBundle 的一条上下文内容。
- ContextSelection：候选信息的选择日志，记录 included / excluded 和原因。
- ContextPolicy：上下文选择策略，集中管理预算、信任、敏感信息和 required context。
- ContextMetrics：上下文构造指标，支持观测和复盘。
- ContextCandidate：统一候选模型，后续 state、artifact、memory、trace、resource 都可先转成候选。
- ArtifactCandidate：ContextBuilder 可选择的 artifact 摘要候选，不读取完整 artifact 正文。
- MemoryCandidate：ContextBuilder 可选择的 memory 摘要候选，后续阶段会演进为独立 memory 模块。
- ContextBundle：一次模型调用或 step 执行所需的结构化上下文包。
- ContextBuilder：按照 step 目标、tag、scope、置信度和字符预算选择上下文。

典型关系：
TaskContract + RuntimeState + ArtifactCandidate + MemoryCandidate
  -> ContextBuilder.build(...)
  -> ContextBundle
  -> Model / StepRunner

设计取舍：
当前阶段先用确定性规则验证上下文治理思想，并加入策略、可见性、信任等级、
敏感信息拦截、指标和 required context 检查。不引入向量检索、LLM 总结或复杂记忆系统。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from runtime_core.contracts import TaskContract
from runtime_core.state import RuntimeState, StepExecution, StepStatus


class ContextSourceType(str, Enum):
    """上下文来源类型。

    - GOAL：任务目标，始终进入上下文。
    - CURRENT_STEP：当前步骤说明，始终进入上下文。
    - STEP_SUMMARY：历史步骤摘要，只保留最近少量已完成步骤。
    - ARTIFACT_REF：结构化产物引用，只进入摘要和引用，不默认进入完整正文。
    - MEMORY：跨任务或项目记忆，必须通过 scope、tag 和置信度筛选。
    - TRACE_SUMMARY：trace 摘要，默认只进入摘要，不进入原始 trace。
    """

    GOAL = "goal"
    CURRENT_STEP = "current_step"
    STEP_SUMMARY = "step_summary"
    ARTIFACT_REF = "artifact_ref"
    MEMORY = "memory"
    TRACE_SUMMARY = "trace_summary"


class ContextVisibility(str, Enum):
    """候选上下文可见性。

    - LLM_VISIBLE：允许进入模型上下文。
    - SUMMARY_ONLY：只允许摘要或引用进入模型上下文。
    - RUNTIME_ONLY：仅 Runtime / 工具可见，不发送给模型。
    """

    LLM_VISIBLE = "llm_visible"
    SUMMARY_ONLY = "summary_only"
    RUNTIME_ONLY = "runtime_only"


class ContextTrustLevel(str, Enum):
    """候选上下文信任等级。

    - SYSTEM：系统或开发者定义的稳定规则。
    - USER：用户输入。
    - TOOL：受控工具输出。
    - ARTIFACT：结构化产物摘要或引用。
    - MEMORY：经过记忆系统管理的信息。
    - EXTERNAL：外部文件、网页、数据库等来源。
    - UNTRUSTED：不可信外部内容，默认不进入模型上下文。
    """

    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    EXTERNAL = "external"
    UNTRUSTED = "untrusted"


class ContextItem(BaseModel):
    """最终进入 ContextBundle 的一条上下文内容。

    ContextItem 是已经通过策略筛选、预算裁剪和安全检查的信息。通常会被
    `to_prompt_sections()` 渲染为模型可见上下文。
    """

    source_type: ContextSourceType = Field(description="上下文来源类型。")
    source_id: str = Field(description="来源标识，例如 artifact id、memory id 或 step id。")
    title: str = Field(description="上下文片段标题，用于 prompt section 或调试输出。")
    content: str = Field(description="进入上下文的正文或摘要。")
    visibility: ContextVisibility = Field(
        default=ContextVisibility.LLM_VISIBLE,
        description="可见性。用于区分完整可见、仅摘要可见和 Runtime-only。",
    )
    trust_level: ContextTrustLevel = Field(
        default=ContextTrustLevel.SYSTEM,
        description="信任等级。用于判断外部或不可信内容是否能进入模型上下文。",
    )
    sensitive: bool = Field(default=False, description="是否包含敏感信息。默认策略会排除敏感候选。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="来源相关扩展元数据。")


class ContextSelection(BaseModel):
    """候选信息的一条选择日志。

    selection log 是 Context Builder 的可解释性基础。它记录候选为什么进入、
    为什么被排除，以及排除是否因为预算、信任、敏感、过期或不相关。
    """

    source_type: ContextSourceType = Field(description="候选来源类型。")
    source_id: str = Field(description="候选来源标识。")
    included: bool = Field(description="该候选是否最终进入 ContextBundle.items。")
    reason: str = Field(description="进入或排除原因，供调试、复盘和测试断言使用。")
    score: float = Field(default=0.0, description="简单相关性分数，目前主要来自 tag overlap。")
    tags: list[str] = Field(default_factory=list, description="候选标签。")
    visibility: ContextVisibility = Field(default=ContextVisibility.LLM_VISIBLE, description="候选可见性。")
    trust_level: ContextTrustLevel = Field(default=ContextTrustLevel.SYSTEM, description="候选信任等级。")
    sensitive: bool = Field(default=False, description="候选是否被标记为敏感。")


class ContextPolicy(BaseModel):
    """上下文选择策略。

    ContextPolicy 把可变规则从 ContextBuilder 中抽出来。不同 step 或不同
    Agent 可以传入不同 policy，避免把策略写死在构造逻辑里。
    """

    max_recent_steps: int = Field(default=3, description="最多保留最近多少条 step 摘要。")
    max_item_chars: int = Field(default=500, description="单条上下文内容的最大字符数。")
    max_context_chars: int = Field(default=3000, description="整个 ContextBundle 的最大字符预算。")
    min_memory_confidence: float = Field(default=0.6, description="memory 候选进入上下文的最低置信度。")
    include_trace_summary: bool = Field(default=True, description="是否允许 trace summary 进入上下文。")
    allow_untrusted_external_context: bool = Field(
        default=False,
        description="是否允许 untrusted 候选进入模型上下文。默认关闭。",
    )
    exclude_sensitive: bool = Field(default=True, description="是否排除 sensitive 候选。默认开启。")
    required_source_ids: list[str] = Field(
        default_factory=list,
        description="当前 step 必须具备的 source id。缺失时 bundle.ready=False。",
    )
    required_artifact_types: list[str] = Field(
        default_factory=list,
        description="当前 step 必须具备的 artifact type。缺失时 bundle.ready=False。",
    )


class ContextMetrics(BaseModel):
    """一次上下文构造的观测指标。

    Metrics 让上下文工程可以被观察和测试，而不是只看最终 prompt。
    后续可以进入 trace，用于复盘上下文变化对结果的影响。
    """

    total_chars: int = Field(default=0, description="估算上下文字符数。")
    item_count: int = Field(default=0, description="最终进入 ContextBundle.items 的数量。")
    included_count: int = Field(default=0, description="selection_log 中 included=True 的数量。")
    excluded_count: int = Field(default=0, description="selection_log 中 included=False 的数量。")
    source_type_breakdown: dict[str, int] = Field(default_factory=dict, description="按 source_type 统计进入项数量。")
    budget_used_ratio: float = Field(default=0.0, description="字符预算使用比例。")
    sensitive_excluded_count: int = Field(default=0, description="因 sensitive 被排除的候选数量。")
    untrusted_excluded_count: int = Field(default=0, description="因 untrusted 被排除的候选数量。")
    missing_required_count: int = Field(default=0, description="缺失 required context 的数量。")


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

    当前它只是阶段 1 的轻量模型。阶段 2 会演进为正式 `MemoryRecord`。
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


class ContextBundle(BaseModel):
    """当前 step 的结构化上下文包。

    ContextBundle 是 ContextBuilder 的主要输出。它同时包含模型可见内容、
    选择日志、指标和 required context 检查结果。
    """

    task_id: str = Field(description="任务 ID。")
    task_type: str = Field(description="任务类型。")
    step_id: str = Field(description="当前 step id。")
    goal: str = Field(description="任务目标。")
    current_step: str = Field(description="当前 step 描述。")
    items: list[ContextItem] = Field(default_factory=list, description="最终进入上下文的条目。")
    selection_log: list[ContextSelection] = Field(default_factory=list, description="候选选择日志。")
    metrics: ContextMetrics = Field(default_factory=ContextMetrics, description="上下文构造指标。")
    estimated_chars: int = Field(default=0, description="估算上下文字符数。")
    excluded_count: int = Field(default=0, description="被排除的候选数量。")
    ready: bool = Field(default=True, description="required context 是否满足。False 表示当前 step 不应继续。")
    missing_required_context: list[str] = Field(default_factory=list, description="缺失的 required source 或 artifact type。")
    blocked_reason: str = Field(default="", description="ready=False 时的阻塞原因。")

    def to_prompt_sections(self) -> list[str]:
        """将结构化上下文渲染为稳定的 prompt section。"""
        sections = [
            f"# Goal\n{self.goal}",
            f"# Current Step\n{self.current_step}",
        ]
        for item in self.items:
            sections.append(f"# {item.title}\n{item.content}")
        return sections


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
        artifacts: list[ArtifactCandidate] | None = None,
        memories: list[MemoryCandidate] | None = None,
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
                    content=self._truncate(content, policy=active_policy),
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
                        content=self._truncate(candidate.content, policy=active_policy),
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
        bounded_items = self._apply_context_budget(items, selection_log, policy=active_policy)
        missing_required_context = self._find_missing_required_context(bounded_items, active_policy)
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
        score = self._score_by_tags(memory.tags, step_tags)
        if score <= 0:
            return False, "memory tag 与当前 step 无关。", 0.0
        return True, "memory 通过 scope、tag、置信度和有效期筛选。", score

    def _collect_candidates(
        self,
        *,
        contract: TaskContract,
        artifacts: list[ArtifactCandidate],
        memories: list[MemoryCandidate],
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
        collected.extend(
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
            for artifact in artifacts
        )

        # MemoryCandidate 当前仍是阶段 1 的轻量模型；转换为 ContextCandidate 后
        # 会在 _select_memory() 中执行 scope、tag、confidence、expires_at 检查。
        collected.extend(
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
            for memory in memories
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
        score = self._score_by_tags(candidate.tags, step_tags)
        if score <= 0:
            return False, "candidate tag 与当前 step 无关，避免污染上下文。", 0.0
        if candidate.source_type == ContextSourceType.ARTIFACT_REF:
            return True, "artifact tag 与当前 step tag 匹配，只引用摘要和路径。", score
        return True, "candidate tag 与当前 step tag 匹配。", score

    def _score_by_tags(self, candidate_tags: list[str], step_tags: list[str]) -> float:
        candidate = set(_normalize_tags(candidate_tags))
        current = set(step_tags)
        if not candidate or not current:
            return 0.0
        overlap = candidate & current
        if not overlap:
            return 0.0
        return min(1.0, 0.5 + len(overlap) / max(len(current), 1))

    def _truncate(self, value: str, *, policy: ContextPolicy) -> str:
        if len(value) <= policy.max_item_chars:
            return value
        return value[: policy.max_item_chars - 20].rstrip() + "\n...[truncated]"

    def _apply_context_budget(
        self,
        items: list[ContextItem],
        selection_log: list[ContextSelection],
        *,
        policy: ContextPolicy,
    ) -> list[ContextItem]:
        """按 ContextPolicy.max_context_chars 执行总字符预算控制。"""
        selected: list[ContextItem] = []
        used = 0
        for item in items:
            next_used = used + len(item.content)
            if next_used <= policy.max_context_chars:
                selected.append(item)
                used = next_used
                continue

            # 候选之前可能已经被标记 included=True。预算裁剪发生在最后，
            # 因此这里要同步回写 selection_log，保持解释日志和最终 items 一致。
            for decision in selection_log:
                if (
                    decision.source_type == item.source_type
                    and decision.source_id == item.source_id
                    and decision.included
                ):
                    decision.included = False
                    decision.reason = f"{decision.reason} 但超过 ContextBuilder 字符预算，已排除。"
                    decision.score = 0.0
                    break
            else:
                selection_log.append(
                    ContextSelection(
                        source_type=item.source_type,
                        source_id=item.source_id,
                        included=False,
                        reason="超过 ContextBuilder 字符预算，已排除。",
                        score=0.0,
                        tags=list(item.metadata.get("tags", [])),
                    )
                )
        return selected

    def _find_missing_required_context(
        self,
        items: list[ContextItem],
        policy: ContextPolicy,
    ) -> list[str]:
        """检查当前 step 声明的 required context 是否真的进入了最终上下文。"""
        missing: list[str] = []
        included_ids = {item.source_id for item in items}
        included_artifact_types = {
            str(item.metadata.get("artifact_type"))
            for item in items
            if item.metadata.get("artifact_type")
        }
        for source_id in policy.required_source_ids:
            if source_id not in included_ids:
                missing.append(f"source_id:{source_id}")
        for artifact_type in policy.required_artifact_types:
            if artifact_type not in included_artifact_types:
                missing.append(f"artifact_type:{artifact_type}")
        return missing

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


def _normalize_tags(tags: list[str]) -> list[str]:
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})


def _is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < datetime.now(timezone.utc)
