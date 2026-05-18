from __future__ import annotations

"""Runtime 状态与步骤执行模型。

Agent Runtime 的主职责不是评测，而是承载一次 Agent 任务的执行过程。
本模块把“任务正在执行到哪一步、每一步输入输出是什么、是否失败、产物是什么”
从业务 adapter 中抽出来，成为 Runtime Core 的公共能力。

主要类与关系：
- StepStatus：单个执行步骤的状态枚举。
- StepExecution：一次步骤执行记录，包含 step_id、名称、状态、时间和输入输出摘要。
- RuntimeState：一次任务的运行状态，保存当前步骤、所有步骤记录、产物引用和状态值。
- RuntimeCheckpointStore：把 RuntimeState 持久化为 JSON checkpoint，供失败复盘和后续 resume 使用。

典型关系：
TaskContract -> RuntimeState
AdapterRunContext.run_step(...) -> RuntimeState.start_step / finish_step / fail_step
RuntimeState.steps -> RuntimeTraceRecorder.record(STEP_STARTED / STEP_FINISHED / STEP_FAILED)
RuntimeCheckpointStore.save(...) -> state/*.json
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from runtime.contracts import TaskContract


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StepStatus(str, Enum):
    """步骤状态。

    - PENDING：步骤已计划但尚未开始。
    - RUNNING：步骤正在执行。
    - PASSED：步骤执行成功。
    - FAILED：步骤执行失败。
    - SKIPPED：步骤被运行时策略跳过。
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepExecution(BaseModel):
    """One Runtime-managed execution step."""

    step_id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    inputs_summary: dict[str, Any] = Field(default_factory=dict)
    outputs_summary: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class RuntimeState(BaseModel):
    """Mutable state for one Runtime task execution."""

    task_id: str
    task_type: str
    status: str = "running"
    current_step_id: str | None = None
    steps: list[StepExecution] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_contract(cls, contract: TaskContract) -> "RuntimeState":
        return cls(task_id=contract.task_id, task_type=contract.task_type.value)

    def start_step(
        self,
        *,
        step_id: str,
        name: str,
        inputs_summary: dict[str, Any] | None = None,
    ) -> StepExecution:
        step = StepExecution(
            step_id=step_id,
            name=name,
            status=StepStatus.RUNNING,
            started_at=utc_now(),
            inputs_summary=inputs_summary or {},
        )
        self.current_step_id = step_id
        self.steps.append(step)
        return step

    def finish_step(
        self,
        *,
        step_id: str,
        outputs_summary: dict[str, Any] | None = None,
    ) -> StepExecution:
        step = self._find_step(step_id)
        step.status = StepStatus.PASSED
        step.finished_at = utc_now()
        step.outputs_summary = outputs_summary or {}
        if self.current_step_id == step_id:
            self.current_step_id = None
        return step

    def fail_step(self, *, step_id: str, error: str) -> StepExecution:
        step = self._find_step(step_id)
        step.status = StepStatus.FAILED
        step.finished_at = utc_now()
        step.error = error
        self.status = "failed"
        if self.current_step_id == step_id:
            self.current_step_id = None
        return step

    def add_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)

    def finish(self, status: str) -> None:
        self.status = status
        self.current_step_id = None

    def has_passed_step(self, step_id: str) -> bool:
        return any(
            step.step_id == step_id and step.status == StepStatus.PASSED
            for step in self.steps
        )

    def _find_step(self, step_id: str) -> StepExecution:
        for step in reversed(self.steps):
            if step.step_id == step_id:
                return step
        raise KeyError(f"Runtime step not found: {step_id}")


class RuntimeCheckpointStore:
    """File-backed checkpoint store for one RuntimeState."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: RuntimeState) -> None:
        payload = {
            "checkpointed_at": utc_now(),
            "state": state.model_dump(mode="json"),
        }
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> RuntimeState:
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return RuntimeState.model_validate(payload["state"])

    def exists(self) -> bool:
        return self.state_path.exists()

    def load_or_create(self, contract: TaskContract) -> RuntimeState:
        if self.exists():
            return self.load()
        return RuntimeState.from_contract(contract)
