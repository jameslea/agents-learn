from __future__ import annotations

from runtime.contracts import Budget, RiskLevel, TaskContract, TaskType
from runtime.state import RuntimeCheckpointStore, RuntimeState, StepStatus


def test_runtime_state_tracks_steps_and_artifacts() -> None:
    contract = TaskContract(
        task_id="runtime:state:test",
        task_type=TaskType.CONTENT_GENERATION,
        goal="Deliver a report.",
        risk_level=RiskLevel.LOW,
        budget=Budget(max_attempts=1),
    )
    state = RuntimeState.from_contract(contract)

    started = state.start_step(
        step_id="draft",
        name="Write draft",
        inputs_summary={"topic": "runtime"},
    )
    finished = state.finish_step(
        step_id="draft",
        outputs_summary={"chars": 1200},
    )
    state.add_artifact("runtime:state:test:report")
    state.finish("passed")

    assert started.status == StepStatus.PASSED
    assert finished.outputs_summary == {"chars": 1200}
    assert state.current_step_id is None
    assert state.status == "passed"
    assert state.artifact_ids == ["runtime:state:test:report"]


def test_runtime_checkpoint_store_saves_and_loads_state(tmp_path) -> None:
    contract = TaskContract(
        task_id="runtime:checkpoint:test",
        task_type=TaskType.CONTENT_GENERATION,
        goal="Deliver a report.",
        risk_level=RiskLevel.LOW,
        budget=Budget(max_attempts=1),
    )
    state = RuntimeState.from_contract(contract)
    state.start_step(step_id="outline", name="Generate outline")
    state.finish_step(step_id="outline", outputs_summary={"sections": 3})
    state.finish("passed")

    store = RuntimeCheckpointStore(tmp_path / "state.json")
    store.save(state)
    loaded = store.load()

    assert loaded.task_id == "runtime:checkpoint:test"
    assert loaded.status == "passed"
    assert loaded.steps[0].step_id == "outline"
    assert loaded.steps[0].outputs_summary == {"sections": 3}
