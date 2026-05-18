from __future__ import annotations

"""Agent 项目适配协议。

Agent Runtime 的核心价值不是要求所有 Agent 项目改成同一种内部实现，
而是提供统一运行环境：任务契约、trace、artifact、评估结果和治理事件。
本模块定义一个最小 AgentAdapter 协议，让不同范式的 Agent 项目可以通过
adapter 接入 Runtime。

主要类与关系：
- AgentAdapter：项目接入 Runtime 时需要实现的最小协议。
- AdapterRunContext：Runtime 传给 adapter 的上下文，提供 trace 和公共记录方法。
- AgentRunResult：adapter 返回的标准结果，包含 EvaluationResult 和业务 artifact。
- AgentAdapterExecution：Runtime 完成一次 adapter 执行后的完整记录。
- run_id：可选运行实例标识；为空时使用兼容旧路径，非空时隔离 trace/state/artifact/lock。
- RuntimeState：Runtime 为一次任务维护的步骤、产物和状态值。
- RuntimeCheckpointStore：RuntimeState 的本地 checkpoint 持久化。
- LocalArtifactStore：保存较大的 step 输出和最终产物，state / trace 只保存引用。
- RuntimeRunLock：阻止同一个 adapter 并发写入同一组 trace/checkpoint/artifact。
- RuntimeRunManifest：记录一次运行的 trace、checkpoint、artifact root 和最终状态。
- run_agent_adapter：统一运行入口，负责记录 task_started、artifact_created、
  evaluation_run 和 task_finished。
- run_agent_adapter_detailed：和 run_agent_adapter 使用同一生命周期，但返回完整执行记录。

典型关系：
AgentAdapter.describe_contract() -> TaskContract
AgentAdapter.run(context) -> AgentRunResult
AgentRunResult.artifacts -> RuntimeTraceRecorder.record(ARTIFACT_CREATED, ...)
AgentRunResult.evaluation -> EvaluationArtifact / EvaluationResult
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar

from runtime.artifact_store import LocalArtifactStore
from runtime.artifacts import Artifact, EvaluationArtifact
from runtime.contracts import TaskContract
from runtime.evaluation import EvaluationResult
from runtime.manifest import RuntimeRunManifest, RuntimeRunManifestStore
from runtime.run_lock import RuntimeRunLock
from runtime.state import RuntimeCheckpointStore, RuntimeState, utc_now
from runtime.trace import RuntimeTraceRecorder, TraceEventType


T = TypeVar("T")


@dataclass
class AgentRunResult:
    """Standard output returned by an AgentAdapter."""

    evaluation: EvaluationResult
    artifacts: list[Artifact] = field(default_factory=list)


@dataclass
class AgentAdapterExecution:
    """Complete Runtime record for one adapter execution."""

    contract: TaskContract
    evaluation: EvaluationResult
    artifacts: list[Artifact] = field(default_factory=list)
    run_id: str | None = None
    trace_path: Path | None = None
    artifact_root: Path | None = None
    manifest_path: Path | None = None
    state: RuntimeState | None = None
    checkpoint_path: Path | None = None


@dataclass
class AdapterRunContext:
    """Runtime services exposed to an adapter during one run."""

    contract: TaskContract
    trace: RuntimeTraceRecorder
    state: RuntimeState
    run_id: str | None = None
    checkpoint_store: RuntimeCheckpointStore | None = None
    artifact_store: LocalArtifactStore | None = None
    resume: bool = False

    def record_tool_call(self, tool_name: str, inputs: dict[str, Any] | None = None) -> None:
        self.trace.record(
            TraceEventType.TOOL_CALLED,
            {
                "task_id": self.contract.task_id,
                "tool_name": tool_name,
                "inputs": inputs or {},
            },
        )

    def run_step(
        self,
        *,
        step_id: str,
        name: str,
        run: Callable[[], T],
        inputs_summary: dict[str, Any] | None = None,
        outputs_summary: Callable[[T], dict[str, Any]] | dict[str, Any] | None = None,
        output_key: str | None = None,
    ) -> T:
        """Run one Runtime-managed step with state and trace events."""
        if (
            self.resume
            and output_key is not None
            and self.state.has_passed_step(step_id)
            and output_key in self.state.values
        ):
            self.trace.record(
                TraceEventType.STEP_SKIPPED,
                {
                    "task_id": self.contract.task_id,
                    "step_id": step_id,
                    "name": name,
                    "reason": f"Resume reused checkpoint output: {output_key}",
                },
            )
            return self.state.values[output_key]

        step = self.state.start_step(
            step_id=step_id,
            name=name,
            inputs_summary=inputs_summary,
        )
        self.save_checkpoint()
        self.trace.record(TraceEventType.STEP_STARTED, step)
        try:
            result = run()
        except Exception as error:
            failed_step = self.state.fail_step(step_id=step_id, error=str(error))
            self.save_checkpoint()
            self.trace.record(TraceEventType.STEP_FAILED, failed_step)
            raise

        if callable(outputs_summary):
            output_data = outputs_summary(result)
        else:
            output_data = outputs_summary or {}
        if output_key is not None:
            self.state.values[output_key] = result
        finished_step = self.state.finish_step(
            step_id=step_id,
            outputs_summary=output_data,
        )
        self.save_checkpoint()
        self.trace.record(TraceEventType.STEP_FINISHED, finished_step)
        return result

    def save_checkpoint(self) -> None:
        if self.checkpoint_store is not None:
            self.checkpoint_store.save(self.state)


class AgentAdapter(Protocol):
    """Minimal protocol for connecting an Agent project to Runtime."""

    adapter_id: str
    trace_name: str

    def describe_contract(self) -> TaskContract:
        """Return the task contract Runtime should execute."""

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        """Run the project-specific logic and return structured artifacts."""


def run_agent_adapter_detailed(
    adapter: AgentAdapter,
    *,
    trace_dir: Path,
    resume: bool = False,
    run_id: str | None = None,
) -> AgentAdapterExecution:
    """Run one adapter and return the full Runtime execution record."""
    run_id = _normalize_run_id(run_id)
    with RuntimeRunLock(_lock_path(adapter, trace_dir, run_id)):
        contract = adapter.describe_contract()
        trace_path = _trace_path(adapter, trace_dir, run_id)
        artifact_root = _artifact_root(trace_dir, run_id)
        checkpoint_store = RuntimeCheckpointStore(_checkpoint_path(adapter, trace_dir, run_id))
        manifest_store = RuntimeRunManifestStore(_manifest_path(adapter, trace_dir, run_id))
        state = checkpoint_store.load_or_create(contract) if resume else RuntimeState.from_contract(contract)
        if resume:
            state.status = "running"
            state.current_step_id = None
        trace = RuntimeTraceRecorder(trace_path, append=resume)
        checkpoint_store.save(state)
        manifest = RuntimeRunManifest(
            run_id=run_id,
            adapter_id=adapter.adapter_id,
            task_id=contract.task_id,
            trace_path=str(trace_path),
            checkpoint_path=str(checkpoint_store.state_path),
            artifact_root=str(artifact_root),
            metadata={"resume": resume},
        )
        manifest_store.save(manifest)
        trace.record(TraceEventType.TASK_STARTED, contract)

        context = AdapterRunContext(
            contract=contract,
            trace=trace,
            state=state,
            run_id=run_id,
            checkpoint_store=checkpoint_store,
            artifact_store=LocalArtifactStore(artifact_root),
            resume=resume,
        )
        run_result = adapter.run(context)
        for artifact in run_result.artifacts:
            state.add_artifact(artifact.artifact_id)
            checkpoint_store.save(state)
            trace.record(TraceEventType.ARTIFACT_CREATED, artifact)

        evaluation = run_result.evaluation
        state.finish(evaluation.status.value)
        checkpoint_store.save(state)
        manifest.status = evaluation.status.value
        manifest.finished_at = utc_now()
        manifest.metadata.update(
            {
                "score": evaluation.score,
                "reason": evaluation.reason,
                "artifact_count": len(run_result.artifacts),
            }
        )
        manifest_store.save(manifest)
        eval_artifact = EvaluationArtifact(
            artifact_id=f"{contract.task_id}:evaluation",
            task_id=contract.task_id,
            source=adapter.adapter_id,
            status=evaluation.status.value,
            score=evaluation.score,
            metrics=evaluation.metrics,
            reason=evaluation.reason,
        )
        trace.record(TraceEventType.EVALUATION_RUN, eval_artifact)
        trace.record(TraceEventType.TASK_FINISHED, evaluation)
        return AgentAdapterExecution(
            contract=contract,
            evaluation=evaluation,
            artifacts=list(run_result.artifacts),
            run_id=run_id,
            trace_path=trace_path,
            artifact_root=artifact_root,
            manifest_path=manifest_store.manifest_path,
            state=state,
            checkpoint_path=checkpoint_store.state_path,
        )


def run_agent_adapter(
    adapter: AgentAdapter,
    *,
    trace_dir: Path,
    resume: bool = False,
    run_id: str | None = None,
) -> EvaluationResult:
    """Run one adapter through the common Runtime lifecycle."""
    return run_agent_adapter_detailed(
        adapter,
        trace_dir=trace_dir,
        resume=resume,
        run_id=run_id,
    ).evaluation


def _normalize_run_id(run_id: str | None) -> str | None:
    if run_id is None:
        return None
    cleaned = run_id.strip()
    if not cleaned:
        return None
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"Invalid runtime run_id: {run_id}")
    return cleaned


def _trace_path(adapter: AgentAdapter, trace_dir: Path, run_id: str | None) -> Path:
    if run_id is None:
        return trace_dir / adapter.trace_name
    return trace_dir / run_id / adapter.trace_name


def _artifact_root(trace_dir: Path, run_id: str | None) -> Path:
    root = trace_dir.parent / "artifacts"
    if run_id is None:
        return root
    return root / run_id


def _checkpoint_path(adapter: AgentAdapter, trace_dir: Path, run_id: str | None) -> Path:
    state_dir = trace_dir.parent / "state"
    if run_id is not None:
        state_dir = state_dir / run_id
    return state_dir / f"{Path(adapter.trace_name).stem}.state.json"


def _manifest_path(adapter: AgentAdapter, trace_dir: Path, run_id: str | None) -> Path:
    manifest_dir = trace_dir.parent / "manifests"
    if run_id is not None:
        manifest_dir = manifest_dir / run_id
    return manifest_dir / f"{Path(adapter.trace_name).stem}.manifest.json"


def _lock_path(adapter: AgentAdapter, trace_dir: Path, run_id: str | None) -> Path:
    state_dir = trace_dir.parent / "state"
    if run_id is not None:
        state_dir = state_dir / run_id
    return state_dir / f"{Path(adapter.trace_name).stem}.lock"
