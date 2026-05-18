from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime.trace_replay import render_timeline, summarize_trace


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_TRACE_DIR = PROJECT_DIR / "traces"


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay runtime JSONL traces as readable timelines.")
    parser.add_argument(
        "trace",
        nargs="?",
        default=None,
        help="Trace JSONL file. Defaults to the latest trace in the project traces directory.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    args = parser.parse_args()

    trace_path = Path(args.trace) if args.trace else _latest_trace(DEFAULT_TRACE_DIR)
    if args.json:
        summary = summarize_trace(trace_path)
        print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(render_timeline(trace_path))


def _latest_trace(trace_dir: Path) -> Path:
    traces = sorted(trace_dir.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not traces:
        raise SystemExit(f"No trace files found in {trace_dir}")
    return traces[0]


if __name__ == "__main__":
    main()
