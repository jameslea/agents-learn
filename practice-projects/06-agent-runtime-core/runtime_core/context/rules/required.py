from __future__ import annotations

from runtime_core.context.bundle import ContextItem
from runtime_core.context.policy import ContextPolicy


def find_missing_required_context(items: list[ContextItem], policy: ContextPolicy) -> list[str]:
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
