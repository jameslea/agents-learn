from __future__ import annotations

from runtime_core.context.bundle import ContextItem
from runtime_core.context.policy import ContextPolicy
from runtime_core.context.selection import ContextSelection


def truncate(value: str, *, policy: ContextPolicy) -> str:
    if len(value) <= policy.max_item_chars:
        return value
    return value[: policy.max_item_chars - 20].rstrip() + "\n...[truncated]"


def apply_context_budget(
    items: list[ContextItem],
    selection_log: list[ContextSelection],
    *,
    policy: ContextPolicy,
) -> list[ContextItem]:
    selected: list[ContextItem] = []
    used = 0
    for item in items:
        next_used = used + len(item.content)
        if next_used <= policy.max_context_chars:
            selected.append(item)
            used = next_used
            continue

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
