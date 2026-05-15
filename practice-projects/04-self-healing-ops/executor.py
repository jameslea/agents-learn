from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from state import RunResult


def prepare_workspace(source_path: Path, workspace_root: Path) -> tuple[Path, Path]:
    """把 challenge task 复制到独立工作目录。

    自愈过程只修改 workspace 内的副本，原始题目文件保持不变，方便反复评估。
    """
    task_name = source_path.stem
    workspace_path = workspace_root / task_name
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    target_path = workspace_path / source_path.name
    shutil.copy2(source_path, target_path)
    return workspace_path, target_path


def run_python_file(path: Path, timeout_seconds: float = 5.0) -> RunResult:
    """在文件所在目录中执行目标脚本，并捕获 stdout/stderr/timeout。"""
    command = ["python3", str(path.name)]
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - start
        return RunResult(
            command=command,
            exit_code=completed.returncode,
            timed_out=False,
            stdout=_clip(completed.stdout),
            stderr=_clip(completed.stderr),
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        return RunResult(
            command=command,
            exit_code=None,
            timed_out=True,
            stdout=_clip(exc.stdout or ""),
            stderr=_clip(exc.stderr or ""),
            duration_seconds=duration,
        )


def _clip(text: str, limit: int = 4000) -> str:
    """限制 trace 中保存的输出长度，保留尾部通常更接近真实错误。"""
    if len(text) <= limit:
        return text
    return text[-limit:]
