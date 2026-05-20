from __future__ import annotations

"""最小 Runtime 串联器。

MinimalRuntime 不是通用 Agent 框架。它只把前五个阶段已经验证过的能力
组合成一个小核心，供具体场景调用：

- RuntimeState：记录任务进度。
- ContextBuilder：构造当前 step 工作视图。
- MemoryStore：提供可复用记忆。
- ArtifactStore：保存和消费 schema artifact。
- FileCheckpointStore：保存可恢复状态。
- TraceRecorder：记录可复盘事件。

业务 step 仍由场景代码实现，Runtime 只提供公共支撑。
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from runtime_core.artifact import ArtifactRecord
from runtime_core.artifact import ArtifactStore
from runtime_core.observability.checkpoint import FileCheckpointStore
from runtime_core.context import ContextBuilder, ContextBundle, ContextPolicy
from runtime_core.task import TaskContract
from runtime_core.memory import MemoryQuery, MemoryRecord, MemoryStore
from runtime_core.task import RuntimeState, StepStatus
from runtime_core.observability.trace import TraceEventType, TraceReader, TraceRecorder, TraceReplaySummary


class BlockedReason(BaseModel):
    """Runtime 进入 blocked 状态时给人的处理说明。"""

    step_id: str = Field(description="被阻塞的 step。")
    reason: str = Field(description="阻塞原因。")
    suggested_action: str = Field(description="建议人工处理方式。")


class MinimalRuntime:
    """阶段 6 使用的最小 Runtime Core。"""

    def __init__(
        self,
        *,
        contract: TaskContract,
        checkpoint_path: str | Path,
        trace_path: str | Path,
        artifact_snapshot_path: str | Path | None = None,
        artifact_schemas: dict[str, type[BaseModel]] | None = None,
        memories: list[MemoryRecord] | None = None,
        reset: bool = False,
    ) -> None:
        self.contract = contract
        self.artifact_schemas = artifact_schemas or {}
        self.checkpoint_store = FileCheckpointStore(checkpoint_path)
        self.artifact_snapshot_path = Path(artifact_snapshot_path) if artifact_snapshot_path else Path(checkpoint_path).with_name("artifacts.json")
        self.trace_recorder = TraceRecorder(trace_path, reset=reset)
        self.trace_reader = TraceReader(trace_path)
        self.context_builder = ContextBuilder()
        self.memory_store = MemoryStore(memories or [])
        self.artifact_store = ArtifactStore(schemas=self.artifact_schemas)

        if reset:
            self.checkpoint_store.clear()
            if self.artifact_snapshot_path.exists():
                self.artifact_snapshot_path.unlink()
        if self.checkpoint_store.exists():
            self.state = self.checkpoint_store.load().state
            self.resumed = True
        else:
            self.state = RuntimeState.from_contract(contract)
            self.resumed = False
        self._load_artifact_snapshot()

    def start_task(self) -> None:
        """记录任务开始事件。恢复运行时不重复写入 task_started。"""
        if not self.resumed:
            self.trace_recorder.task_started(
                task_id=self.contract.task_id,
                task_type=self.contract.task_type.value,
                goal_summary=self.contract.goal,
            )

    def build_context(
        self,
        *,
        step_id: str,
        current_step: str,
        step_tags: list[str] | None = None,
        required_artifact_types: list[str] | None = None,
    ) -> ContextBundle:
        """为当前 step 构造 ContextBundle。"""
        memories = [
            result.record
            for result in self.memory_store.search(
                MemoryQuery(scopes=["global", self.contract.task_type.value, self.contract.task_id], tags=step_tags or [])
            )
        ]
        return self.context_builder.build(
            contract=self.contract,
            state=self.state,
            step_id=step_id,
            current_step=current_step,
            step_tags=step_tags or [],
            artifacts=self.artifact_store.list_records(),
            memories=memories,
            policy=ContextPolicy(required_artifact_types=required_artifact_types or []),
        )

    def start_step(self, *, step_id: str, name: str, inputs_summary: dict[str, Any] | None = None) -> None:
        """启动 step，并记录 trace。"""
        self.state.start_step(step_id=step_id, name=name, inputs_summary=inputs_summary)
        self.trace_recorder.record(
            event_type=TraceEventType.STEP_STARTED,
            task_id=self.contract.task_id,
            step_id=step_id,
            summary=f"Step started: {name}",
            data={"input_summary": inputs_summary or {}},
        )
        self.save_checkpoint()

    def pass_step(self, *, step_id: str, outputs_summary: dict[str, Any] | None = None) -> None:
        """完成 step，并记录 trace 和 checkpoint。"""
        self.state.finish_step(step_id=step_id, outputs_summary=outputs_summary)
        self.trace_recorder.record(
            event_type=TraceEventType.STEP_PASSED,
            task_id=self.contract.task_id,
            step_id=step_id,
            summary=f"Step passed: {step_id}",
            data={"output_summary": outputs_summary or {}},
        )
        self.save_checkpoint()

    def skip_step(self, *, step_id: str, reason: str) -> bool:
        """如果 step 已经成功执行过，则记录 skipped 并返回 True。"""
        if not self.has_passed_step(step_id):
            return False
        self.state.start_step(step_id=step_id, name=f"Skip completed step: {step_id}", inputs_summary={"reason": reason})
        self.state.finish_step(step_id=step_id, outputs_summary={"skipped": True})
        self.state.steps[-1].status = StepStatus.SKIPPED
        self.trace_recorder.record(
            event_type=TraceEventType.STEP_PASSED,
            task_id=self.contract.task_id,
            step_id=step_id,
            summary=f"Step skipped: {step_id}",
            data={"reason": reason},
        )
        self.save_checkpoint()
        return True

    def fail_step(self, *, step_id: str, error: str, recoverable: bool = True) -> None:
        """标记 step 失败，并记录 trace。"""
        self.state.fail_step(step_id=step_id, error=error)
        self.trace_recorder.record(
            event_type=TraceEventType.STEP_FAILED,
            task_id=self.contract.task_id,
            step_id=step_id,
            summary=error,
            data={"error": error},
            risk="medium",
            recoverable=recoverable,
        )
        self.save_checkpoint()

    def block(self, *, step_id: str, reason: str, suggested_action: str) -> BlockedReason:
        """进入 blocked 终态，并写入 human_required trace。"""
        blocked = BlockedReason(step_id=step_id, reason=reason, suggested_action=suggested_action)
        try:
            self.state.block_step(step_id=step_id, error=reason)
        except KeyError:
            self.state.status = "blocked"
        self.state.values["blocked_reason"] = blocked.model_dump(mode="json")
        self.trace_recorder.record(
            event_type=TraceEventType.HUMAN_REQUIRED,
            task_id=self.contract.task_id,
            step_id=step_id,
            summary=reason,
            data=blocked.model_dump(mode="json"),
            risk="high",
            recoverable=True,
        )
        self.save_checkpoint()
        return blocked

    def save_artifact(self, record: ArtifactRecord) -> ArtifactRecord:
        """保存 artifact 并记录 artifact_created trace。"""
        saved = self.artifact_store.save(record)
        if saved.artifact_id not in self.state.artifact_ids:
            self.state.artifact_ids.append(saved.artifact_id)
        self.trace_recorder.record(
            event_type=TraceEventType.ARTIFACT_CREATED,
            task_id=self.contract.task_id,
            step_id=saved.producer_step_id,
            summary=f"Artifact created: {saved.artifact_id}",
            data={
                "artifact_id": saved.artifact_id,
                "artifact_type": saved.artifact_type,
                "schema_name": saved.schema_name,
                "path": saved.path,
            },
        )
        self._save_artifact_snapshot()
        self.save_checkpoint()
        return saved

    def consume_artifact(self, *, artifact_id: str, schema_name: str, consumer_step_id: str):
        """读取 artifact payload 并记录 artifact_consumed trace。"""
        payload = self.artifact_store.load_payload(artifact_id, schema_name=schema_name)
        self.trace_recorder.record(
            event_type=TraceEventType.ARTIFACT_CONSUMED,
            task_id=self.contract.task_id,
            step_id=consumer_step_id,
            summary=f"Artifact consumed: {artifact_id}",
            data={
                "artifact_id": artifact_id,
                "schema_name": schema_name,
                "consumer_step_id": consumer_step_id,
            },
        )
        return payload

    def finish_task(self, *, final_status: str = "completed", summary: str = "") -> None:
        """结束任务，保存 checkpoint 并记录 task_finished。"""
        self.state.status = final_status
        self.save_checkpoint()
        self.trace_recorder.task_finished(
            task_id=self.contract.task_id,
            final_status=final_status,
            summary=summary or f"Task finished with status {final_status}",
        )

    def save_checkpoint(self) -> None:
        self.checkpoint_store.save(self.state)

    def trace_summary(self) -> TraceReplaySummary:
        return self.trace_reader.replay()

    def has_passed_step(self, step_id: str) -> bool:
        return any(step.step_id == step_id and step.status == StepStatus.PASSED for step in self.state.steps)

    def _save_artifact_snapshot(self) -> None:
        self.artifact_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.model_dump(mode="json") for record in self.artifact_store.list_records()]
        self.artifact_snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_artifact_snapshot(self) -> None:
        if not self.artifact_snapshot_path.exists():
            return
        payload = json.loads(self.artifact_snapshot_path.read_text(encoding="utf-8"))
        self.artifact_store = ArtifactStore(
            (ArtifactRecord.model_validate(item) for item in payload),
            schemas=self.artifact_schemas,
        )
