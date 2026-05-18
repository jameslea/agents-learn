from __future__ import annotations

import json

import pytest

from runtime.run_lock import RuntimeRunAlreadyActive, RuntimeRunLock


def test_runtime_run_lock_blocks_existing_lock(tmp_path) -> None:
    lock_path = tmp_path / "state" / "content.lock"

    with RuntimeRunLock(lock_path):
        assert lock_path.exists()
        with pytest.raises(RuntimeRunAlreadyActive):
            with RuntimeRunLock(lock_path):
                pass

    assert not lock_path.exists()


def test_runtime_run_lock_releases_after_exception(tmp_path) -> None:
    lock_path = tmp_path / "state" / "content.lock"

    with pytest.raises(ValueError):
        with RuntimeRunLock(lock_path):
            raise ValueError("boom")

    assert not lock_path.exists()


def test_runtime_run_lock_clears_stale_pid_lock(tmp_path) -> None:
    lock_path = tmp_path / "state" / "content.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps({"pid": -1, "locked_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    with RuntimeRunLock(lock_path):
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        assert payload["pid"] > 0

    assert not lock_path.exists()
