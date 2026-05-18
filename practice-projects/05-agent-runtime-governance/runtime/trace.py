from __future__ import annotations

"""可回放 trace 记录。

RuntimeTraceRecorder 按 JSONL 记录任务开始、工具调用、artifact 生成、
评估、阻塞和结束事件。trace 的目标不是普通日志，而是让一次 Agent
任务在失败后可以复盘：做了什么、用了什么工具、生成了什么证据、为什么停下。

主要类与关系：
- TraceEventType：Runtime 支持的事件类型，包括 task_started、step_started、
  step_finished、tool_called、tool_decision、artifact_created、evaluation_run、
  guardrail_blocked、task_finished 等。
- RuntimeTraceRecorder：最小 JSONL trace 记录器。默认每次运行覆盖同名 trace，
  一行一个事件，payload 可以是 dict 或 Pydantic model。

典型关系：
TaskContract -> task_started
GovernedToolRunner.call(...) -> tool_called
Artifact -> artifact_created
EvaluationArtifact / EvaluationResult -> evaluation_run / task_finished

设计取舍：
当前先使用本地 JSONL，便于阅读、测试和回放；后续可适配 Langfuse、Phoenix 或 LangSmith。
如果确实要把多个任务写入同一个 trace 文件，可以显式传入 append=True。
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class TraceEventType(str, Enum):
    """Runtime trace 事件类型。

    - TASK_STARTED：任务开始，通常记录 TaskContract。
    - STEP_STARTED：Runtime 开始执行一个任务步骤。
    - STEP_FINISHED：Runtime 成功完成一个任务步骤。
    - STEP_FAILED：Runtime 执行步骤失败。
    - STEP_SKIPPED：Runtime resume 时跳过已经完成且有缓存输出的步骤。
    - TOOL_DECISION：工具调用前的策略决策，说明允许、拦截或需要人工审核。
    - TOOL_CALLED：工具被调用，记录工具名、风险等级和输入摘要。
    - ARTIFACT_CREATED：结构化产物生成，记录 artifact 内容或引用。
    - HUMAN_REVIEW_REQUESTED：自动流程需要人工确认才能继续。
    - HUMAN_REVIEW_DECIDED：人工审核已经给出批准、拒绝或修改要求。
    - VALIDATION_RUN：验证器执行，记录验证输入、结果和失败原因。
    - EVALUATION_RUN：评估器执行，记录评分、状态和指标。
    - GUARDRAIL_BLOCKED：安全护栏或工具策略拦截了动作。
    - TASK_FINISHED：任务结束，记录最终 EvaluationResult 或终态摘要。
    """

    TASK_STARTED = "task_started"
    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"
    STEP_FAILED = "step_failed"
    STEP_SKIPPED = "step_skipped"
    TOOL_DECISION = "tool_decision"
    TOOL_CALLED = "tool_called"
    ARTIFACT_CREATED = "artifact_created"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_REVIEW_DECIDED = "human_review_decided"
    VALIDATION_RUN = "validation_run"
    EVALUATION_RUN = "evaluation_run"
    GUARDRAIL_BLOCKED = "guardrail_blocked"
    TASK_FINISHED = "task_finished"


class RuntimeTraceRecorder:
    """Per-run JSONL trace recorder for runtime events."""

    def __init__(self, trace_path: Path, *, append: bool = False):
        self.trace_path = trace_path
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        if not append:
            self.trace_path.write_text("", encoding="utf-8")

    def record(self, event: TraceEventType, payload: dict[str, Any] | BaseModel) -> None:
        if isinstance(payload, BaseModel):
            data = payload.model_dump(mode="json")
        else:
            data = payload
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.value,
            "payload": data,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
