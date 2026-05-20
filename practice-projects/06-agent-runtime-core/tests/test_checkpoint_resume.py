from __future__ import annotations

from pathlib import Path

from runtime_core.observability import FileCheckpointStore
from runtime_core.task import TaskContract, TaskType
from runtime_core.task import RuntimeState, StepStatus
from runtime_core.execution import StepDefinition, StepRunner


def _contract() -> TaskContract:
    return TaskContract(
        task_id="test:resume",
        task_type=TaskType.RESEARCH,
        goal="Validate checkpoint resume.",
    )


def _steps(executed: list[str]) -> list[StepDefinition]:
    def handler(step_id: str):
        def run(_: RuntimeState) -> dict[str, int | str]:
            executed.append(step_id)
            return {"step_id": step_id, "count": len(executed)}

        return run

    return [
        StepDefinition(step_id="collect", name="Collect", handler=handler("collect")),
        StepDefinition(step_id="summarize", name="Summarize", handler=handler("summarize")),
        StepDefinition(step_id="review", name="Review", handler=handler("review")),
    ]


def test_checkpoint_store_saves_and_loads_runtime_state(tmp_path: Path) -> None:
    contract = _contract()
    state = RuntimeState.from_contract(contract)
    state.start_step(step_id="collect", name="Collect")
    state.finish_step(step_id="collect", outputs_summary={"sources": 3})

    store = FileCheckpointStore(tmp_path / "checkpoint.json")
    saved = store.save(state)
    loaded = store.load()

    assert store.exists()
    assert saved.task_id == contract.task_id
    assert loaded.task_id == contract.task_id
    assert loaded.state.steps[0].step_id == "collect"
    assert loaded.state.steps[0].status == StepStatus.PASSED


def test_step_runner_resumes_without_repeating_completed_steps(tmp_path: Path) -> None:
    executed: list[str] = []
    contract = _contract()
    state = RuntimeState.from_contract(contract)
    store = FileCheckpointStore(tmp_path / "checkpoint.json")
    runner = StepRunner(store)

    first_report = runner.run(
        state=state,
        steps=_steps(executed),
        stop_after_step_id="summarize",
    )
    assert first_report.interrupted is True
    assert first_report.completed_steps == ["collect", "summarize"]
    assert executed == ["collect", "summarize"]

    restored = store.load().state
    second_report = runner.run(state=restored, steps=_steps(executed))

    assert second_report.interrupted is False
    assert second_report.skipped_steps == ["collect", "summarize"]
    assert second_report.completed_steps == ["review"]
    assert executed == ["collect", "summarize", "review"]
    assert restored.status == "completed"
    assert [step.status for step in restored.steps].count(StepStatus.SKIPPED) == 2


def test_step_runner_saves_checkpoint_after_each_completed_step(tmp_path: Path) -> None:
    executed: list[str] = []
    contract = _contract()
    state = RuntimeState.from_contract(contract)
    store = FileCheckpointStore(tmp_path / "checkpoint.json")

    StepRunner(store).run(
        state=state,
        steps=_steps(executed),
        stop_after_step_id="collect",
    )
    loaded = store.load().state

    assert loaded.status == "interrupted"
    assert any(step.step_id == "collect" and step.status == StepStatus.PASSED for step in loaded.steps)
    assert not any(step.step_id == "summarize" and step.status == StepStatus.PASSED for step in loaded.steps)
