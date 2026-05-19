from __future__ import annotations

"""Runtime Core 的任务状态模型。

State 保存一次 Agent 任务已经执行到哪里，以及每个 step 的状态和摘要。
它不是长期记忆，也不是 artifact store；它只描述当前任务的执行进度。

主要类与关系：
- StepStatus：单个 step 的状态枚举。
- StepExecution：单个 step 的输入、输出、时间和错误摘要。
- RuntimeState：一次任务的运行状态，可为 ContextBuilder 提供最近 step 摘要。

典型关系：
TaskContract -> RuntimeState
RuntimeState.steps -> ContextBuilder 最近 step 摘要
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from runtime_core.contracts import TaskContract


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StepStatus(str, Enum):
    """步骤状态。

    - PENDING：已计划但尚未开始。
    - RUNNING：正在执行。
    - PASSED：执行成功。
    - FAILED：执行失败。
    - BLOCKED：因权限、预算、缺少人工决策等原因被阻塞。
    - SKIPPED：恢复执行时跳过已完成步骤。
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class StepExecution(BaseModel):
    """单个 Runtime step 的执行记录。

    StepExecution 保存的是摘要，不保存完整输入输出正文。完整产物应进入
    artifact，完整执行过程应进入 trace。
    """

    step_id: str = Field(description="step 唯一标识，用于恢复、跳过和 trace 关联。")
    name: str = Field(description="面向人类阅读的 step 名称。")
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="当前 step 状态。",
    )
    started_at: str | None = Field(default=None, description="step 开始时间，UTC ISO 格式。")
    finished_at: str | None = Field(default=None, description="step 结束时间，UTC ISO 格式。")
    inputs_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="输入摘要，只保存足以复盘的短信息，不保存完整上下文或大文件。",
    )
    outputs_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="输出摘要，只保存关键结果、计数、artifact id 等引用信息。",
    )
    error: str = Field(default="", description="失败摘要。完整错误堆栈后续应进入 trace。")


class RuntimeState(BaseModel):
    """一次任务的可变执行状态，只记录进度和少量运行时值。"""

    task_id: str = Field(description="任务 ID，来自 TaskContract。")
    task_type: str = Field(description="任务类型，来自 TaskContract.task_type。")
    status: str = Field(default="running", description="任务整体状态。")
    current_step_id: str | None = Field(default=None, description="当前执行中的 step id。")
    steps: list[StepExecution] = Field(
        default_factory=list,
        description="按时间顺序记录的 step 执行列表。",
    )
    artifact_ids: list[str] = Field(
        default_factory=list,
        description="当前任务产生或引用的 artifact id。",
    )
    values: dict[str, Any] = Field(
        default_factory=dict,
        description="少量运行时键值状态。",
    )

    @classmethod
    def from_contract(cls, contract: TaskContract) -> "RuntimeState":
        """从任务契约创建初始状态。"""
        return cls(task_id=contract.task_id, task_type=contract.task_type.value)

    def start_step(
        self,
        *,
        step_id: str,
        name: str,
        inputs_summary: dict[str, Any] | None = None,
    ) -> StepExecution:
        """创建 RUNNING step，并将其设为当前 step。"""
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
        """将 step 标记为 PASSED；找不到 step_id 时抛出 KeyError。"""
        step = self._find_step(step_id)
        step.status = StepStatus.PASSED
        step.finished_at = utc_now()
        step.outputs_summary = outputs_summary or {}
        if self.current_step_id == step_id:
            self.current_step_id = None
        return step

    def fail_step(self, *, step_id: str, error: str) -> StepExecution:
        """将 step 标记为 FAILED，并同步任务整体状态。"""
        step = self._find_step(step_id)
        step.status = StepStatus.FAILED
        step.finished_at = utc_now()
        step.error = error
        self.status = "failed"
        if self.current_step_id == step_id:
            self.current_step_id = None
        return step

    def _find_step(self, step_id: str) -> StepExecution:
        """从后往前查找最近一次匹配的 step。"""
        for step in reversed(self.steps):
            if step.step_id == step_id:
                return step
        raise KeyError(f"Runtime step not found: {step_id}")
