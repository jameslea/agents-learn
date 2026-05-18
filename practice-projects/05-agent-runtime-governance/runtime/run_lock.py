from __future__ import annotations

"""Runtime run lock.

同一个 adapter 的 trace、checkpoint 和 artifact 目前共享固定文件名。
如果两个进程同时运行同一个 adapter，就会出现 trace 交错、checkpoint 覆盖等问题。
本模块提供一个最小文件锁：通过原子创建 `.lock` 文件阻止并发写入。
它只做本地单机安全处理：如果 lock 中记录的 pid 已经不存在，则认为是
stale lock 并清理；如果 pid 仍活跃，绝不自动删除。

主要类与关系：
- RuntimeRunLock：上下文管理器，进入时创建锁文件，退出时删除锁文件。
- RuntimeRunAlreadyActive：锁已存在时抛出，调用方可以提示用户稍后再试。

典型关系：
run_agent_adapter_detailed -> RuntimeRunLock -> RuntimeTraceRecorder / RuntimeCheckpointStore
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RuntimeRunAlreadyActive(RuntimeError):
    """Raised when a runtime lock already exists for the adapter run."""


class RuntimeStaleLockCleared(RuntimeWarning):
    """Marker warning class for cleared stale locks."""


class RuntimeRunLock:
    """Small file lock based on atomic exclusive create."""

    def __init__(self, lock_path: Path, *, clear_stale: bool = True) -> None:
        self.lock_path = lock_path
        self.clear_stale = clear_stale
        self._acquired = False

    def __enter__(self) -> "RuntimeRunLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_lock()
        self._acquired = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._acquired:
            return
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        self._acquired = False

    def _create_lock(self) -> None:
        payload = {
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "lock_path": str(self.lock_path),
            "pid": os.getpid(),
        }
        try:
            with self.lock_path.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
        except FileExistsError as error:
            if self.clear_stale and self._clear_if_stale():
                with self.lock_path.open("x", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
                return
            raise RuntimeRunAlreadyActive(
                f"Runtime run already active for lock: {self.lock_path}"
            ) from error

    def _clear_if_stale(self) -> bool:
        lock_data = self._read_lock_data()
        pid = lock_data.get("pid")
        if not isinstance(pid, int):
            return False
        if _pid_is_alive(pid):
            return False
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            return True
        return True

    def _read_lock_data(self) -> dict[str, Any]:
        try:
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
