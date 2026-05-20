from __future__ import annotations

import json
from pathlib import Path

from runtime_core.observability.checkpoint.record import CheckpointRecord
from runtime_core.task import RuntimeState


class FileCheckpointStore:
    """基于本地 JSON 文件的最小 checkpoint store。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        """checkpoint 文件是否存在。"""
        return self.path.exists()

    def save(self, state: RuntimeState) -> CheckpointRecord:
        """保存当前 RuntimeState 快照。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = CheckpointRecord(task_id=state.task_id, state=state)
        self.path.write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record

    def load(self) -> CheckpointRecord:
        """读取 checkpoint。文件不存在时抛出 FileNotFoundError。"""
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return CheckpointRecord.model_validate(payload)

    def clear(self) -> None:
        """删除 checkpoint 文件。"""
        if self.path.exists():
            self.path.unlink()
