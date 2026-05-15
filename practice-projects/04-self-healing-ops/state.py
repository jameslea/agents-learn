from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class ErrorKind(str, Enum):
    """自愈闭环内部统一使用的错误分类。

    Agent 不直接读取完整 traceback，而是围绕这些稳定分类做决策。
    """

    NONE = "none"
    IMPORT_ERROR = "import_error"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    ASSERTION_ERROR = "assertion_error"
    SECURITY_BLOCKED = "security_blocked"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN = "unknown"


class FinalStatus(str, Enum):
    """任务最终状态。

    blocked 表示安全系统正确拒绝执行危险代码，不应和 failed 混为一类。
    """

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class RunResult(BaseModel):
    """一次受限脚本执行的原始结果。"""

    command: list[str]
    exit_code: Optional[int] = None
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


class ErrorSummary(BaseModel):
    """从执行结果或安全检查结果中压缩出的修复输入。"""

    kind: ErrorKind
    message: str
    evidence: str = ""
    line_number: Optional[int] = None


class SafetyIssue(BaseModel):
    """AST 安全扫描发现的危险语法点。"""

    line_number: int
    kind: str
    message: str


class VerificationResult(BaseModel):
    """一次客观验证的结论。

    passed=True 是唯一成功信号；Agent 的文字说明不算通过。
    """

    passed: bool
    reason: str
    run_result: Optional[RunResult] = None
    safety_issues: list[SafetyIssue] = Field(default_factory=list)


class RepairAttempt(BaseModel):
    """一次“分类错误 -> 尝试修复 -> 再验证”的完整记录。"""

    attempt: int
    error: ErrorSummary
    repair_summary: str
    changed: bool
    verification: VerificationResult


class PatchProposal(BaseModel):
    """LLM RepairAgent 输出的结构化 patch 建议。

    当前只支持整文件替换，后续可以扩展为 unified diff 或多文件 patch。
    """

    should_patch: bool
    summary: str
    patched_source: str = ""


class SelfHealState(BaseModel):
    """单个 challenge task 在自愈过程中的全量状态。"""

    task_name: str
    source_path: Path
    workspace_path: Path
    target_path: Path
    max_attempts: int = 3
    attempts: list[RepairAttempt] = Field(default_factory=list)
    final_status: FinalStatus = FinalStatus.PENDING
    final_reason: str = ""

    model_config = {"arbitrary_types_allowed": True}
