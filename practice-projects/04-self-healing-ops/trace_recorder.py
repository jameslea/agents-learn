from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class TraceRecorder:
    """按 JSONL 记录自愈过程。

    一行一个事件，便于用 cat、jq 或日志系统按时间顺序复盘。
    """

    def __init__(self, trace_path: Path):
        self.trace_path = trace_path
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, payload: dict[str, Any] | BaseModel) -> None:
        """记录一个事件；Pydantic 对象会先转成可 JSON 序列化的字典。"""
        if isinstance(payload, BaseModel):
            data = payload.model_dump(mode="json")
        else:
            data = payload
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": data,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
