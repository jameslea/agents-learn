from __future__ import annotations

"""评估结果定义。

EvaluationResult 是 Runtime 的统一出口之一，用来表达任务是否通过、
失败原因、评分和可机器读取的指标。它让不同场景的结果可以被汇总、
回归测试和横向比较，而不是只停留在终端日志。

主要类与关系：
- RuntimeFinalStatus：Runtime 层统一终态。passed / failed / blocked / needs_human /
  cancelled 用来消除不同项目各自定义状态造成的混乱。
- EvaluationResult：单个任务的评估结果，绑定 task_id、状态、分数、原因和指标。
- EvaluationSummary：多个 EvaluationResult 的聚合结果，用于批量运行和跨项目汇总。

典型关系：
scenario / adapter -> EvaluationResult
EvaluationResult -> EvaluationArtifact -> trace
list[EvaluationResult] -> EvaluationSummary -> JSON report / CLI summary

注意：
blocked 在安全任务中可以算 effective success，因为正确拒绝危险动作也是成功治理。
"""

from collections import Counter
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RuntimeFinalStatus(str, Enum):
    """Runtime 层统一终态。

    - PASSED：任务通过，且有客观验证、规则评估或人工确认支撑。
    - FAILED：任务未通过，通常是验证失败、评分不足或达到重试上限。
    - BLOCKED：任务被安全策略或工具策略正确拦截。对安全任务来说，这可能是有效成功。
    - NEEDS_HUMAN：自动流程不能安全继续，需要人工确认或补充判断。
    - CANCELLED：任务被人工或调度系统取消，不再继续执行。
    """

    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    CANCELLED = "cancelled"


class EvaluationResult(BaseModel):
    """Machine-readable evaluation result for one task."""

    task_id: str
    task_name: str
    status: RuntimeFinalStatus
    score: float
    attempts: int
    reason: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    """Aggregated result for a batch of runtime evaluation cases."""

    total: int
    passed: int
    blocked: int
    failed: int
    effective_success_rate: float
    repair_success_rate: float
    average_attempts: float
    metrics: dict[str, Any] = Field(default_factory=dict)
    results: list[EvaluationResult]

    @classmethod
    def from_results(cls, results: list[EvaluationResult]) -> "EvaluationSummary":
        total = len(results)
        counts = Counter(result.status for result in results)
        passed = counts[RuntimeFinalStatus.PASSED]
        blocked = counts[RuntimeFinalStatus.BLOCKED]
        failed = counts[RuntimeFinalStatus.FAILED]
        attempts = [result.attempts for result in results]
        return cls(
            total=total,
            passed=passed,
            blocked=blocked,
            failed=failed,
            effective_success_rate=(passed + blocked) / total if total else 0.0,
            repair_success_rate=passed / total if total else 0.0,
            average_attempts=sum(attempts) / len(attempts) if attempts else 0.0,
            metrics={
                "needs_human": counts[RuntimeFinalStatus.NEEDS_HUMAN],
                "cancelled": counts[RuntimeFinalStatus.CANCELLED],
            },
            results=results,
        )
