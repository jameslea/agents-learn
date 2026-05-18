from __future__ import annotations

from runtime.artifact_store import LocalArtifactStore


def test_local_artifact_store_saves_text_and_json(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    text_ref = store.save_text(
        task_id="content_runtime:lite",
        name="draft",
        text="# Draft\n",
    )
    json_ref = store.save_json(
        task_id="content_runtime:lite",
        name="review",
        data={"score": 73},
    )

    assert text_ref.path == "content_runtime_lite/draft.md"
    assert json_ref.path == "content_runtime_lite/review.json"
    assert store.read_text(text_ref) == "# Draft\n"
    assert store.read_json(json_ref) == {"score": 73}
