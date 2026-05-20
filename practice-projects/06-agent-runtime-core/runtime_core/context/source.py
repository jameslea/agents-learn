from __future__ import annotations

from enum import Enum


class ContextSourceType(str, Enum):
    """上下文来源类型。

    - GOAL：任务目标，始终进入上下文。
    - CURRENT_STEP：当前步骤说明，始终进入上下文。
    - STEP_SUMMARY：历史步骤摘要，只保留最近少量已完成步骤。
    - ARTIFACT_REF：结构化产物引用，只进入摘要和引用，不默认进入完整正文。
    - MEMORY：跨任务或项目记忆，必须通过 scope、tag 和置信度筛选。
    - TRACE_SUMMARY：trace 摘要，默认只进入摘要，不进入原始 trace。
    """

    GOAL = "goal"
    CURRENT_STEP = "current_step"
    STEP_SUMMARY = "step_summary"
    ARTIFACT_REF = "artifact_ref"
    MEMORY = "memory"
    TRACE_SUMMARY = "trace_summary"

class ContextVisibility(str, Enum):
    """候选上下文可见性。

    - LLM_VISIBLE：允许进入模型上下文。
    - SUMMARY_ONLY：只允许摘要或引用进入模型上下文。
    - RUNTIME_ONLY：仅 Runtime / 工具可见，不发送给模型。
    """

    LLM_VISIBLE = "llm_visible"
    SUMMARY_ONLY = "summary_only"
    RUNTIME_ONLY = "runtime_only"

class ContextTrustLevel(str, Enum):
    """候选上下文信任等级。

    - SYSTEM：系统或开发者定义的稳定规则。
    - USER：用户输入。
    - TOOL：受控工具输出。
    - ARTIFACT：结构化产物摘要或引用。
    - MEMORY：经过记忆系统管理的信息。
    - EXTERNAL：外部文件、网页、数据库等来源。
    - UNTRUSTED：不可信外部内容，默认不进入模型上下文。
    """

    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    EXTERNAL = "external"
    UNTRUSTED = "untrusted"
