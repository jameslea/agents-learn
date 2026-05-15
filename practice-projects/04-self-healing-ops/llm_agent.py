from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.llm_factory import build_llm  # noqa: E402
from state import ErrorSummary, PatchProposal  # noqa: E402


class LLMRepairAgent:
    """可选 LLM 修复 Agent。

    它只负责提出结构化 patch proposal。是否真正修好，仍由本地安全检查和再次执行决定。
    """

    def __init__(self, max_source_chars: int = 12000):
        self.max_source_chars = max_source_chars
        self.llm = build_llm(temperature=0.1, json_mode=True)

    def repair(self, path: Path, error: ErrorSummary) -> tuple[bool, str]:
        original = path.read_text(encoding="utf-8")
        proposal = self._propose_patch(original, error)
        if not proposal.should_patch:
            return False, proposal.summary
        if not proposal.patched_source.strip():
            return False, "LLM proposed a patch but patched_source was empty."
        if proposal.patched_source == original:
            return False, f"LLM patch made no changes: {proposal.summary}"

        path.write_text(proposal.patched_source, encoding="utf-8")
        return True, f"LLM patch applied: {proposal.summary}"

    def _propose_patch(self, source: str, error: ErrorSummary) -> PatchProposal:
        prompt = self._build_prompt(source, error)
        response = self.llm.invoke(prompt)
        try:
            return PatchProposal.model_validate_json(response.content)
        except (ValidationError, ValueError):
            return PatchProposal.model_validate(_extract_json_object(response.content))

    def _build_prompt(self, source: str, error: ErrorSummary) -> str:
        clipped_source = source[-self.max_source_chars :]
        return f"""
你是一个谨慎的 Python 代码修复 Agent。

目标：
- 修复给定单文件 Python 脚本中的错误。
- 只做最小必要改动。
- 不新增网络、shell、删除文件、动态执行等危险能力。
- 不解释长篇原因，只返回 JSON。

错误分类：{error.kind.value}
错误消息：{error.message}
错误证据：
{error.evidence}

当前源码：
```python
{clipped_source}
```

必须返回合法 JSON 对象，字段如下：
{{
  "should_patch": true或false,
  "summary": "一句话说明修复",
  "patched_source": "完整修复后的 Python 源码；should_patch=false 时为空字符串"
}}
""".strip()


def _extract_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(text[start : end + 1])
