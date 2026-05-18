from __future__ import annotations

"""本地 Artifact Store。

Artifact Store 负责保存较大的中间产物和最终产物，让 RuntimeState 和 trace
只保存引用与摘要。这样 Runtime 可以管理产物生命周期，而不是把长文本、
LLM 输出或报告正文直接塞进 state / trace。

主要类与关系：
- ArtifactRef：一个已保存产物的引用，包含 artifact_id、相对路径、媒体类型和摘要。
- LocalArtifactStore：本地文件实现，支持保存文本和 JSON，并按 task_id 分目录。

典型关系：
AdapterRunContext.artifact_store -> LocalArtifactStore
step output -> LocalArtifactStore.save_text / save_json -> ArtifactRef
RuntimeState.values -> artifact_ref dict
resume -> LocalArtifactStore.read_text / read_json
"""

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    """Reference to one file-backed runtime artifact."""

    artifact_id: str
    path: str
    media_type: str
    size_bytes: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class LocalArtifactStore:
    """File-backed artifact store for one runtime project."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_text(
        self,
        *,
        task_id: str,
        name: str,
        text: str,
        extension: str = ".md",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        path = self._path(task_id, name, extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return self._ref(task_id=task_id, name=name, path=path, media_type="text/markdown", metadata=metadata)

    def save_json(
        self,
        *,
        task_id: str,
        name: str,
        data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        path = self._path(task_id, name, ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._ref(task_id=task_id, name=name, path=path, media_type="application/json", metadata=metadata)

    def read_text(self, artifact_ref: ArtifactRef | dict[str, Any]) -> str:
        ref = _coerce_ref(artifact_ref)
        return (self.root_dir / ref.path).read_text(encoding="utf-8")

    def read_json(self, artifact_ref: ArtifactRef | dict[str, Any]) -> Any:
        ref = _coerce_ref(artifact_ref)
        return json.loads((self.root_dir / ref.path).read_text(encoding="utf-8"))

    def _path(self, task_id: str, name: str, extension: str) -> Path:
        clean_task = _slug(task_id)
        clean_name = _slug(name)
        clean_extension = extension if extension.startswith(".") else f".{extension}"
        return self.root_dir / clean_task / f"{clean_name}{clean_extension}"

    def _ref(
        self,
        *,
        task_id: str,
        name: str,
        path: Path,
        media_type: str,
        metadata: dict[str, Any] | None,
    ) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=f"{task_id}:{name}",
            path=str(path.relative_to(self.root_dir)),
            media_type=media_type,
            size_bytes=path.stat().st_size,
            metadata=metadata or {},
        )


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")
    return cleaned or "artifact"


def _coerce_ref(artifact_ref: ArtifactRef | dict[str, Any]) -> ArtifactRef:
    if isinstance(artifact_ref, ArtifactRef):
        return artifact_ref
    return ArtifactRef.model_validate(artifact_ref)
