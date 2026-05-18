from __future__ import annotations

"""B-runtime-lite：内容团队项目的最小真实执行 adapter。

这个模块和 content_team_adapter.py 的区别是：
- content_team_adapter.py 观测已有 final_report.md，不重新执行 B 项目。
- content_runtime_adapter.py 从 topic 开始执行一个最小内容生成链路。

主要类与关系：
- ContentRuntimeLiteAdapter：标准 AgentAdapter，实现 B 项目的最小 Runtime execution。
- run_content_runtime_lite：CLI 和测试使用的便捷入口。
- GovernedToolRunner：执行 outline、draft、review、revise、write 等受治理工具。

典型关系：
topic -> content_runtime.generate_outline -> content_runtime.write_draft
-> content_runtime.review_draft -> content_runtime.create_improvement_plan
-> content_runtime.revise_draft -> content_runtime.write_final_report
-> ContentReportArtifact / EvaluationResult
"""

import sys
from pathlib import Path
from typing import Any

from runtime.agent_adapter import AdapterRunContext, AgentRunResult, run_agent_adapter
from runtime.artifact_store import ArtifactRef
from runtime.artifacts import ContentReportArtifact, ImprovementPlanArtifact
from runtime.contracts import Budget, HumanReviewPolicy, RiskLevel, TaskContract, TaskType
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus
from runtime.tools import GovernedToolRunner, ToolPolicy, ToolRegistry, ToolSpec


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]
CONTENT_PROJECT_DIR = REPO_ROOT / "practice-projects" / "02-content-creation-team"

if str(CONTENT_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(CONTENT_PROJECT_DIR))

from utils.report_evaluation import evaluate_report_quality  # noqa: E402
from adapters.content_team_adapter import _recommendation_for_issue  # noqa: E402


DEFAULT_TOPIC = "Agent Runtime 如何支撑可控的内容生产流程"


def run_content_runtime_lite(
    *,
    topic: str = DEFAULT_TOPIC,
    trace_dir: Path,
    output_dir: Path,
    guardrail_score: int = 70,
    resume: bool = False,
    run_id: str | None = None,
) -> EvaluationResult:
    """Run the minimal content runtime execution adapter."""
    adapter = ContentRuntimeLiteAdapter(
        topic=topic,
        output_dir=output_dir,
        guardrail_score=guardrail_score,
    )
    return run_agent_adapter(adapter, trace_dir=trace_dir, resume=resume, run_id=run_id)


class ContentRuntimeLiteAdapter:
    """Minimal runtime execution adapter for project B."""

    adapter_id = "content_runtime_lite"
    trace_name = "content_runtime_lite.runtime.jsonl"

    def __init__(self, *, topic: str, output_dir: Path, guardrail_score: int) -> None:
        self.topic = topic.strip() or DEFAULT_TOPIC
        self.output_dir = output_dir
        self.guardrail_score = guardrail_score

    def describe_contract(self) -> TaskContract:
        return TaskContract(
            task_id="content_runtime:lite",
            task_type=TaskType.CONTENT_GENERATION,
            goal=f"Deliver a minimal content report for topic: {self.topic}",
            inputs={
                "topic": self.topic,
                "output_dir": str(self.output_dir),
                "guardrail_score": self.guardrail_score,
            },
            expected_outputs=[
                "ContentReportArtifact",
                "ImprovementPlanArtifact",
                "EvaluationResult",
            ],
            success_criteria=[
                "a final report is written inside the approved output directory",
                "the draft is reviewed and revised before final delivery",
                "quality guardrail metrics are recorded without becoming the task goal",
            ],
            risk_level=RiskLevel.MEDIUM,
            allowed_tools=[
                "content_runtime.generate_outline",
                "content_runtime.write_draft",
                "content_runtime.review_draft",
                "content_runtime.create_improvement_plan",
                "content_runtime.revise_draft",
                "content_runtime.write_final_report",
                "content_runtime.check_delivery",
            ],
            budget=Budget(max_attempts=1, timeout_seconds=10.0, max_tool_calls=10),
            human_review_policy=HumanReviewPolicy.NEVER,
        )

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        output_base = self.output_dir / context.run_id if context.run_id else self.output_dir
        output_path = output_base / "content_runtime_lite_report.md"
        registry = _registry()
        policy = ToolPolicy.from_contract(
            context.contract,
            allowed_read_dirs=[str(self.output_dir.resolve())],
            allowed_write_dirs=[str(self.output_dir.resolve())],
        )
        runner = GovernedToolRunner(
            registry=registry,
            policy=policy,
            trace=context.trace,
            task_id=context.contract.task_id,
        )
        if context.artifact_store is None:
            raise RuntimeError("Content runtime requires an artifact store.")
        artifact_store = context.artifact_store

        outline_ref = context.run_step(
            step_id="outline",
            name="Generate report outline",
            inputs_summary={"topic": self.topic},
            run=lambda: artifact_store.save_json(
                task_id=context.contract.task_id,
                name="outline",
                data=runner.call("content_runtime.generate_outline", topic=self.topic),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="outline_ref",
        )
        outline = artifact_store.read_json(outline_ref)

        draft_ref = context.run_step(
            step_id="draft",
            name="Write first draft",
            inputs_summary={"sections": len(outline)},
            run=lambda: artifact_store.save_text(
                task_id=context.contract.task_id,
                name="draft",
                text=runner.call("content_runtime.write_draft", topic=self.topic, outline=outline),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="draft_ref",
        )
        draft_markdown = artifact_store.read_text(draft_ref)
        context.state.values["draft_chars"] = len(draft_markdown)
        context.save_checkpoint()

        draft_review_ref = context.run_step(
            step_id="review",
            name="Review draft as guardrail",
            inputs_summary={"draft_chars": len(draft_markdown)},
            run=lambda: artifact_store.save_json(
                task_id=context.contract.task_id,
                name="draft_review",
                data=runner.call("content_runtime.review_draft", markdown=draft_markdown),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="draft_review_ref",
        )
        draft_review = artifact_store.read_json(draft_review_ref)
        context.state.values["draft_quality_score"] = draft_review["total_score"]
        context.save_checkpoint()

        plan_ref = context.run_step(
            step_id="plan",
            name="Create improvement plan",
            inputs_summary={"issues": len(draft_review["issues"])},
            run=lambda: artifact_store.save_json(
                task_id=context.contract.task_id,
                name="improvement_plan",
                data=runner.call("content_runtime.create_improvement_plan", review=draft_review),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="improvement_plan_ref",
        )
        plan = artifact_store.read_json(plan_ref)
        context.state.values["improvement_steps"] = len(plan["steps"])
        context.save_checkpoint()

        final_ref = context.run_step(
            step_id="revise",
            name="Revise draft before delivery",
            inputs_summary={"plan_steps": len(plan["steps"])},
            run=lambda: artifact_store.save_text(
                task_id=context.contract.task_id,
                name="final_report_draft",
                text=runner.call(
                    "content_runtime.revise_draft",
                    markdown=draft_markdown,
                    plan=plan,
                ),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="final_ref",
        )
        final_markdown = artifact_store.read_text(final_ref)

        write_result = context.run_step(
            step_id="deliver",
            name="Write final report",
            inputs_summary={"output_path": str(output_path), "final_chars": len(final_markdown)},
            run=lambda: runner.call(
                "content_runtime.write_final_report",
                output_path=str(output_path),
                markdown=final_markdown,
            ),
            outputs_summary=lambda value: {"report_path": value["report_path"]},
            output_key="write_result",
        )
        delivery_ref = context.run_step(
            step_id="check_delivery",
            name="Check final delivery",
            inputs_summary={"report_path": write_result["report_path"]},
            run=lambda: artifact_store.save_json(
                task_id=context.contract.task_id,
                name="delivery",
                data=runner.call("content_runtime.check_delivery", report_path=write_result["report_path"]),
            ).model_dump(mode="json"),
            outputs_summary=lambda value: _ref_summary(value),
            output_key="delivery_ref",
        )
        delivery = artifact_store.read_json(delivery_ref)
        context.state.values["final_report_path"] = write_result["report_path"]
        context.state.values["final_quality_score"] = delivery["quality"]["total_score"]
        context.save_checkpoint()

        delivered = delivery["exists"] and delivery["chars"] > 0 and delivery["revision_applied"]
        status = RuntimeFinalStatus.PASSED if delivered else RuntimeFinalStatus.FAILED
        report_artifact = ContentReportArtifact(
            artifact_id=f"{context.contract.task_id}:content_report",
            task_id=context.contract.task_id,
            source=self.adapter_id,
            report_path=write_result["report_path"],
            total_score=delivery["quality"]["total_score"],
            editorial_score=delivery["quality"]["editorial_score"],
            evidence_score=delivery["quality"]["evidence_score"],
            issues=delivery["quality"]["issues"],
            strengths=delivery["quality"]["strengths"],
            metadata={
                "topic": self.topic,
                "outline_ref": outline_ref,
                "draft_ref": draft_ref,
                "draft_review_ref": draft_review_ref,
                "plan_ref": plan_ref,
                "final_ref": final_ref,
                "delivery_ref": delivery_ref,
                "draft_quality_score": draft_review["total_score"],
                "final_quality_score": delivery["quality"]["total_score"],
                "quality_guardrail_passed": delivery["quality"]["total_score"] >= self.guardrail_score,
                "units": delivery["quality"]["units"],
                "main_sections": delivery["quality"]["main_sections"],
                "subsections": delivery["quality"]["subsections"],
                "references": delivery["quality"]["references"],
                "table_count": delivery["quality"]["table_count"],
            },
        )
        plan_artifact = ImprovementPlanArtifact(
            artifact_id=f"{context.contract.task_id}:improvement_plan",
            task_id=context.contract.task_id,
            source=self.adapter_id,
            plan_id=f"{context.contract.task_id}:improvement_plan",
            summary=plan["summary"],
            steps=plan["steps"],
            issue_ids=plan["issue_ids"],
            metadata={"draft_quality_score": draft_review["total_score"]},
        )
        evaluation = EvaluationResult(
            task_id=context.contract.task_id,
            task_name="B-runtime-lite",
            status=status,
            score=1.0 if delivered else 0.0,
            attempts=1,
            reason=(
                "Final report delivered after draft review and revision."
                if delivered
                else "Final report delivery failed."
            ),
            metrics={
                "topic": self.topic,
                "report_path": write_result["report_path"],
                "artifact_refs": {
                    "outline": outline_ref,
                    "draft": draft_ref,
                    "draft_review": draft_review_ref,
                    "improvement_plan": plan_ref,
                    "final_report_draft": final_ref,
                    "delivery": delivery_ref,
                },
                "delivered": delivered,
                "revision_applied": delivery["revision_applied"],
                "draft_quality": draft_review,
                "final_quality": delivery["quality"],
                "quality_guardrail": {
                    "threshold": self.guardrail_score,
                    "passed": delivery["quality"]["total_score"] >= self.guardrail_score,
                    "score": delivery["quality"]["total_score"],
                },
                "improvement_plan": plan,
            },
        )
        return AgentRunResult(evaluation=evaluation, artifacts=[report_artifact, plan_artifact])


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="content_runtime.generate_outline",
            description="Generate a deterministic report outline for one topic.",
            risk_level=RiskLevel.LOW,
            output_schema="list[str]",
            max_calls=1,
        ),
        _generate_outline,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.write_draft",
            description="Write a deterministic markdown draft from topic and outline.",
            risk_level=RiskLevel.LOW,
            input_schema="topic + outline",
            output_schema="markdown",
            max_calls=1,
        ),
        _write_draft,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.review_draft",
            description="Review the draft and produce quality guardrail metrics.",
            risk_level=RiskLevel.LOW,
            input_schema="markdown",
            output_schema="review dict",
            max_calls=1,
        ),
        _review_draft,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.create_improvement_plan",
            description="Convert draft review issues into a structured improvement plan.",
            risk_level=RiskLevel.LOW,
            input_schema="review",
            output_schema="plan dict",
            max_calls=1,
        ),
        _create_improvement_plan,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.revise_draft",
            description="Revise the draft according to the improvement plan before final delivery.",
            risk_level=RiskLevel.LOW,
            input_schema="markdown + plan",
            output_schema="markdown",
            max_calls=1,
        ),
        _revise_draft,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.write_final_report",
            description="Write final revised report to the approved output directory.",
            risk_level=RiskLevel.MEDIUM,
            input_schema="output_path + markdown",
            output_schema="report_path",
            write_path_args=["output_path"],
            max_calls=1,
        ),
        _write_report,
    )
    registry.register(
        ToolSpec(
            name="content_runtime.check_delivery",
            description="Check final deliverable and record quality guardrail metrics.",
            risk_level=RiskLevel.LOW,
            input_schema="report_path",
            output_schema="delivery dict",
            read_path_args=["report_path"],
            max_calls=1,
        ),
        _check_delivery,
    )
    return registry


def _generate_outline(topic: str) -> list[str]:
    return [
        f"问题定义：{topic}",
        "Runtime 架构与职责边界",
        "内容生产链路的关键阶段",
        "成功案例：结构化产物带来的质量提升",
        "挑战与失败教训：多角色接龙的风险",
        "横向比较：直接 Prompt 与 Runtime 化流程",
        "实施路径：从最小闭环到生产治理",
        "证据边界、交付检查与后续建议",
    ]


def _write_draft(topic: str, outline: list[str]) -> str:
    sections = []
    for index, section in enumerate(outline, 1):
        sections.append(_section_markdown(index, section, topic))
    references = "\n".join(
        [
            "- [1] https://docs.langchain.com/langgraph",
            "- [2] https://docs.dify.ai",
            "- [3] https://docs.smith.langchain.com",
            "- [4] https://arxiv.org/abs/2308.08155",
            "- [5] https://www.anthropic.com/engineering/building-effective-agents",
            "- [6] https://openai.github.io/openai-agents-python/",
            "- [7] https://microsoft.github.io/autogen/",
            "- [8] https://docs.crewai.com",
            "- [9] https://phoenix.arize.com",
            "- [10] https://github.com/NVIDIA/NeMo-Guardrails",
        ]
    )
    return (
        f"# {topic}\n\n"
        "本文由 B-runtime-lite 生成，用于验证内容生产 Agent 是否可以在统一 Runtime 中交付可用产物。"
        "报告刻意保留清晰结构、证据边界和改进入口，方便后续审阅和修订。\n\n"
        + "\n\n".join(sections)
        + "\n\n## 参考资料\n\n"
        + references
        + "\n"
    )


def _section_markdown(index: int, section: str, topic: str) -> str:
    return f"""## {index}. {section}

### {index}.1 核心判断

围绕“{topic}”，本节的核心判断是：Agent 项目的质量瓶颈通常不在单次模型能力，
而在任务契约、工具边界、结构化产物和交付回路是否稳定。Runtime 化流程把这些能力
从临时 prompt 中抽离出来，使内容生产从一次性生成变成可观测、可复盘、可改进的过程。

- 成功案例：当大纲、草稿、评审和改进计划都保存为 artifact 时，失败原因可以被定位。
- 挑战：如果只依赖多角色对话，错误会在上下文中累积，后续角色很难判断事实边界。
- 横向分析：直接 Prompt 适合低风险草稿，Runtime 化流程更适合需要追踪质量和责任的报告。

### {index}.2 实施要点

实践中需要把每一步拆成明确工具：生成大纲、写草稿、审阅草稿、生成改进计划、修订草稿并写出最终文件。
这些工具不应该自由调用，而应由策略控制读写目录、网络权限、调用次数和风险等级。这样做会增加
少量工程成本，但能换来可重复调试和稳定复盘。

| 维度 | 直接 Prompt | Runtime 化流程 |
| --- | --- | --- |
| 质量定位 | 依赖人工阅读 | 依赖 artifact 与指标 |
| 风险边界 | 隐含在提示词中 | 显式写入 ToolPolicy |
| 失败复盘 | 难以回放 | 可通过 trace 回放 |

### {index}.3 证据边界

本节结论来自框架文档、Agent 工程实践和本仓库 A/B/C/D-lite 的实验观察。公开案例和厂商案例
只能说明方向，不等价于所有业务场景都适用。后续若进入生产环境，还需要补充业务数据、
人工审核记录和成本延迟统计。
"""


def _write_report(output_path: str, markdown: str) -> dict[str, str]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return {"report_path": str(path)}


def _review_draft(markdown: str) -> dict[str, Any]:
    return evaluate_report_quality(markdown, name="draft").to_dict()


def _create_improvement_plan(review: dict[str, Any]) -> dict[str, Any]:
    issue_ids = [f"BR{index + 1:02d}" for index, _issue in enumerate(review["issues"])]
    steps = [_recommendation_for_issue(issue) for issue in review["issues"]]
    if not steps:
        steps = ["当前草稿结构已经可交付；后续可补充人工事实核查、数据更新和表达润色。"]
    return {
        "plan_id": "content_runtime:lite:improvement_plan",
        "summary": f"基于 B-runtime-lite 草稿审阅生成 {len(review['issues'])} 条改进建议。",
        "steps": steps,
        "issue_ids": issue_ids,
    }


def _revise_draft(markdown: str, plan: dict[str, Any]) -> str:
    revision_notes = "\n".join(f"- {step}" for step in plan["steps"][:6])
    return (
        markdown.rstrip()
        + "\n\n## 修订说明\n\n"
        + "本节由 Runtime 在交付前根据草稿审阅结果追加，用于说明已经识别的改进方向。"
        + "在完整 Agent 版本中，这一步应由 Writer/Reviser 重新组织正文；当前最小版本先把"
        + "改进计划显式写入最终报告，证明 Runtime 支持审阅后修订。\n\n"
        + revision_notes
        + "\n"
    )


def _check_delivery(report_path: str) -> dict[str, Any]:
    path = Path(report_path)
    markdown = path.read_text(encoding="utf-8") if path.exists() else ""
    return {
        "exists": path.exists(),
        "chars": len(markdown),
        "revision_applied": "## 修订说明" in markdown,
        "quality": evaluate_report_quality(markdown, name=path.name).to_dict(),
    }


def _ref_summary(artifact_ref: dict[str, Any]) -> dict[str, Any]:
    ref = ArtifactRef.model_validate(artifact_ref)
    return {
        "artifact_id": ref.artifact_id,
        "path": ref.path,
        "media_type": ref.media_type,
        "size_bytes": ref.size_bytes,
    }
