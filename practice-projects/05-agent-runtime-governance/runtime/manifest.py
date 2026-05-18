from __future__ import annotations

"""Runtime run manifest.

Manifest 是一次运行的轻量索引文件，用来把 run_id、adapter、trace、state、
artifact root 和最终状态放在同一个 JSON 中。它不是查询系统，也不替代 trace；
它只回答“这次运行的关键产物在哪里”。

主要类与关系：
- RuntimeRunManifest：一次运行的索引记录。
- RuntimeRunManifestStore：负责创建和更新 manifest JSON。

典型关系：
run_agent_adapter_detailed -> RuntimeRunManifestStore.save(running manifest)
adapter.run(...) -> trace/state/artifact
run_agent_adapter_detailed -> RuntimeRunManifestStore.save(finished manifest)
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from runtime.state import utc_now


class RuntimeRunManifest(BaseModel):
    """Small JSON index for one runtime run."""

    run_id: str | None = None
    adapter_id: str
    task_id: str
    trace_path: str
    checkpoint_path: str
    artifact_root: str
    status: str = "running"
    started_at: str = Field(default_factory=utc_now)
    finished_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeRunManifestStore:
    """File-backed manifest store for one runtime run."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, manifest: RuntimeRunManifest) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> RuntimeRunManifest:
        return RuntimeRunManifest.model_validate_json(self.manifest_path.read_text(encoding="utf-8"))

    def exists(self) -> bool:
        return self.manifest_path.exists()
