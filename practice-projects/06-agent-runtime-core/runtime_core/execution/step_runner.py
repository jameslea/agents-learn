from __future__ import annotations

"""Runtime Core 的最小顺序 StepRunner。

StepRunner 只验证 checkpoint / resume 语义：已完成 step 不重复执行，
恢复时显式记录 skipped，执行后保存 checkpoint。
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from runtime_core.observability.checkpoint import FileCheckpointStore
from runtime_core.task import RuntimeState, StepExecution, StepStatus, utc_now


StepHandler = Callable[[RuntimeState], dict[str, Any]]


class StepDefinition(BaseModel):
    """一个可执行 step 的定义。"""

    step_id: str = Field(description="step 唯一标识。")
    name: str = Field(description="step 名称。")
    handler: StepHandler = Field(description="step 执行函数。")

    model_config = {"arbitrary_types_allowed": True}


class StepRunReport(BaseModel):
    """一次 StepRunner 执行报告。"""

    task_id: str = Field(description="任务 ID。")
    completed_steps: list[str] = Field(default_factory=list, description="本次执行完成的 step。")
    skipped_steps: list[str] = Field(default_factory=list, description="恢复时跳过的已完成 step。")
    interrupted: bool = Field(default=False, description="是否按要求模拟中断。")
    final_status: str = Field(description="执行后的任务状态。")


class StepRunner:
    """按顺序执行 step，并在每个 step 后保存 checkpoint。"""

    def __init__(self, checkpoint_store: FileCheckpointStore) -> None:
        self.checkpoint_store = checkpoint_store

    def run(
        self,
        *,
        state: RuntimeState,
        steps: list[StepDefinition],
        stop_after_step_id: str | None = None,
    ) -> StepRunReport:
        """执行 step 列表。

        如果 checkpoint 中已经有某 step 的 PASSED 记录，本次执行会跳过它，
        并额外记录一条 SKIPPED 记录，方便恢复过程可观察。
        """
        report = StepRunReport(task_id=state.task_id, final_status=state.status)

        for step in steps:
            if _has_passed_step(state, step.step_id):
                _record_skipped_step(state, step)
                report.skipped_steps.append(step.step_id)
                self.checkpoint_store.save(state)
                continue

            state.start_step(step_id=step.step_id, name=step.name)
            outputs = step.handler(state)
            state.finish_step(step_id=step.step_id, outputs_summary=outputs)
            report.completed_steps.append(step.step_id)
            self.checkpoint_store.save(state)

            if stop_after_step_id == step.step_id:
                state.status = "interrupted"
                self.checkpoint_store.save(state)
                report.interrupted = True
                report.final_status = state.status
                return report

        state.status = "completed"
        self.checkpoint_store.save(state)
        report.final_status = state.status
        return report


def _has_passed_step(state: RuntimeState, step_id: str) -> bool:
    return any(step.step_id == step_id and step.status == StepStatus.PASSED for step in state.steps)


def _record_skipped_step(state: RuntimeState, step: StepDefinition) -> StepExecution:
    skipped = StepExecution(
        step_id=step.step_id,
        name=f"Skip completed step: {step.name}",
        status=StepStatus.SKIPPED,
        started_at=utc_now(),
        finished_at=utc_now(),
        inputs_summary={"reason": "already passed in checkpoint"},
    )
    state.steps.append(skipped)
    state.current_step_id = None
    return skipped
