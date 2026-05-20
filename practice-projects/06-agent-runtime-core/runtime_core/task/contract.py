from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任务类型。

    - RESEARCH：研究、资料整理、短报告等以信息加工为主的任务。
    - CODE_REVIEW：代码阅读、审查、修复建议等以工程判断为主的任务。
    - CONTENT_GENERATION：内容生成、改写、审阅等文档类任务。
    """

    RESEARCH = "research"
    CODE_REVIEW = "code_review"
    CONTENT_GENERATION = "content_generation"

class TaskContract(BaseModel):
    """一次 Runtime 任务的入口协议。

    TaskContract 是 Runtime 接收任务的稳定边界。它只描述“要做什么”和
    “怎样算完成”，不保存执行进度，也不保存模型上下文。
    """

    task_id: str = Field(description="任务唯一标识，用于关联 state、artifact 和 trace。")
    task_type: TaskType = Field(description="任务类型，用于选择后续策略、工具和上下文规则。")
    goal: str = Field(description="任务目标。通常会进入 ContextBundle，作为当前任务的硬约束。")
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="任务输入参数。适合放用户给定主题、文件路径、配置项等结构化输入。",
    )
    expected_outputs: list[str] = Field(
        default_factory=list,
        description="期望产物名称或类型，用于后续 artifact / evaluation 检查。",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="成功标准。后续可用于评价、停止条件或 required context 检查。",
    )
