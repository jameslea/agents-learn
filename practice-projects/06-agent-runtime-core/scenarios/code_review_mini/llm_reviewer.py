from __future__ import annotations

"""code_review_mini 的可选 LLM 审查器。

LLM 只生成结构化辅助审查意见。场景仍通过 schema 校验、trace 和 blocked
语义约束输出，不把模型自由文本直接交给下游 step。
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from common.llm_factory import build_llm, resolve_provider_config  # noqa: E402
from scenarios.code_review_mini.schemas import CodeFinding, ReviewReport  # noqa: E402


class CodeReviewLLMResult(BaseModel):
    """一次 LLM 审查调用的结构化结果和观测指标。"""

    report: ReviewReport
    provider: str
    model: str
    latency_ms: int = Field(ge=0)
    prompt_chars: int = Field(default=0, ge=0)
    response_chars: int = Field(default=0, ge=0)
    status: str = "success"
    failure_reason: str = ""
    raw_text: str = ""


class CodeReviewLLMReviewer:
    """基于仓库统一 LLM provider 的代码审查器。"""

    def __init__(
        self,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        self.provider_config = resolve_provider_config(provider=provider, model_name=model_name)
        self.llm = build_llm(provider=provider, model_name=model_name, temperature=temperature, json_mode=True)

    def review(self, *, file_path: str, code: str, context_summary: str) -> CodeReviewLLMResult:
        start = time.perf_counter()
        system_prompt = (
            "你是 code_review_mini 场景中的辅助代码审查员。"
            "只返回 JSON，不要返回 Markdown。"
            "你的输出必须能被给定 schema 校验。"
            "不要生成补丁，不要要求执行命令，只做审查发现。"
        )
        user_prompt = (
            "请审查以下 Python 代码，并严格返回 JSON：\n"
            "{\n"
            '  "summary": "一句话摘要",\n'
            '  "findings": [\n'
            "    {\n"
            '      "finding_id": "finding-001",\n'
            '      "severity": "low 或 medium 或 high",\n'
            '      "category": "bug 或 safety 或 maintainability",\n'
            '      "message": "问题描述",\n'
            '      "file_path": "文件路径",\n'
            '      "line_start": 1,\n'
            '      "line_end": 1,\n'
            '      "evidence": "相关代码片段",\n'
            '      "recommendation": "修复建议"\n'
            "    }\n"
            "  ],\n"
            '  "risk_level": "low 或 medium 或 high",\n'
            '  "passed": false,\n'
            '  "reviewer": "llm"\n'
            "}\n\n"
            f"Runtime 上下文摘要：{context_summary}\n"
            f"文件路径：{file_path}\n"
            f"代码：\n{code[:7000]}"
        )
        prompt_chars = len(system_prompt) + len(user_prompt)
        response = self.llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        raw_text = str(response.content)
        report = parse_review_report(raw_text, file_path=file_path)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return CodeReviewLLMResult(
            report=report,
            provider=self.provider_config.name,
            model=self.provider_config.model,
            latency_ms=elapsed_ms,
            prompt_chars=prompt_chars,
            response_chars=len(raw_text),
            raw_text=raw_text,
        )


def parse_review_report(raw_text: str, *, file_path: str) -> ReviewReport:
    """从 LLM 文本中解析 ReviewReport，支持 fenced code block 和前后解释文字。"""
    text = _extract_json(raw_text)
    payload: dict[str, Any] = json.loads(text)
    payload.setdefault("reviewer", "llm")
    for index, finding in enumerate(payload.get("findings", []), start=1):
        finding.setdefault("finding_id", f"finding-{index:03d}")
        finding.setdefault("file_path", file_path)
    return ReviewReport.model_validate(payload)


def deterministic_review(*, file_path: str, code: str) -> ReviewReport:
    """离线审查器，用于单元测试和无网络 demo。"""
    findings: list[CodeFinding] = []
    lines = code.splitlines()
    for index, line in enumerate(lines, start=1):
        if "os.system" in line:
            findings.append(
                CodeFinding(
                    finding_id="finding-001",
                    severity="high",
                    category="safety",
                    message="代码通过 os.system 拼接外部输入执行命令，存在命令注入和破坏性操作风险。",
                    file_path=file_path,
                    line_start=index,
                    line_end=index,
                    evidence=line.strip(),
                    recommendation="改用受控 API，并对输入路径做白名单和边界校验。",
                )
            )
        if line.strip() == "except:":
            findings.append(
                CodeFinding(
                    finding_id=f"finding-{len(findings) + 1:03d}",
                    severity="medium",
                    category="maintainability",
                    message="裸 except 会吞掉未知异常，降低可诊断性。",
                    file_path=file_path,
                    line_start=index,
                    line_end=index,
                    evidence=line.strip(),
                    recommendation="捕获明确异常类型，并记录必要错误信息。",
                )
            )

    risk_level = "high" if any(item.severity == "high" for item in findings) else "low"
    return ReviewReport(
        summary=f"发现 {len(findings)} 个问题。",
        findings=findings,
        risk_level=risk_level,
        passed=not findings,
        reviewer="deterministic",
    )


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
