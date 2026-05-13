import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ContentOutline
from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.outline_evaluation import (
    MAX_OUTLINE_SECTIONS,
    MIN_OUTLINE_SECTIONS,
    OutlineQualityMetrics,
    evaluate_outline_quality,
    validate_outline,
)
from utils.outline_selection import (
    OutlineJudgeResult,
    judge_outline_candidates,
    select_top_outline_metrics,
)

load_dotenv()
logger = get_logger(__name__)

MAX_OUTLINE_ATTEMPTS = 2
DEFAULT_OUTLINE_CANDIDATE_SAMPLES = 5
DEFAULT_OUTLINE_TOP_N = 3


class ProductManager:
    def __init__(self):
        model = os.getenv("MODEL_NAME", "deepseek-chat")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        logger.info("加载 ProductManager LLM: model=%s base_url=%s", model, base_url)
        self.llm = ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def plan_content(self, topic: str) -> ContentOutline:
        """根据主题规划内容大纲"""
        retry_note = ""
        latest_outline = None
        latest_issues = []
        for attempt in range(1, MAX_OUTLINE_ATTEMPTS + 1):
            latest_outline = self.generate_outline_once(topic, retry_note, attempt)

            latest_issues = validate_outline(latest_outline)
            if not latest_issues:
                return latest_outline

            logger.warning(
                "PM 大纲质量门禁发现问题: attempt=%d issues=%s",
                attempt,
                latest_issues,
            )
            retry_note = (
                "\n上一版大纲存在问题："
                + "；".join(latest_issues)
                + "\n请重新规划，避免三段式粗略大纲。"
            )

        raise ValueError(
            "PM 大纲质量门禁未通过：\n"
            + "\n".join(f"- {issue}" for issue in latest_issues)
        )

    def plan_outline_candidates(
        self,
        topic: str,
        samples: int = DEFAULT_OUTLINE_CANDIDATE_SAMPLES,
        top_n: int = DEFAULT_OUTLINE_TOP_N,
        llm_judge: bool = True,
    ) -> tuple[ContentOutline, list[ContentOutline], list[OutlineQualityMetrics], OutlineJudgeResult | None]:
        """生成多个候选大纲，按本地评分筛选，并可选使用 LLM 主编评审选择默认大纲。"""
        candidates: list[ContentOutline] = []
        metrics: list[OutlineQualityMetrics] = []

        for index in range(1, samples + 1):
            logger.info("PM 生成候选大纲: index=%d/%d", index, samples)
            outline = self.plan_content(topic)
            metric = evaluate_outline_quality(outline, name=f"sample_{index}")
            candidates.append(outline)
            metrics.append(metric)
            logger.info(
                "PM 候选大纲评分: name=%s score=%d sections=%d cases=%d specific=%d generic=%d decision=%d",
                metric.name,
                metric.total_score,
                metric.section_count,
                metric.case_sections,
                metric.specific_case_sections,
                metric.generic_case_sections,
                metric.decision_value_sections,
            )

        selected_metrics = select_top_outline_metrics(metrics, top_n)
        metric_by_name = {metric.name: metric for metric in selected_metrics}
        outline_by_name = {
            metric.name: outline
            for outline, metric in zip(candidates, metrics)
            if metric.name in metric_by_name
        }
        selected_candidates = [outline_by_name[metric.name] for metric in selected_metrics]

        judge_result = judge_outline_candidates(topic, selected_metrics) if llm_judge and selected_metrics else None
        chosen_name = selected_metrics[0].name if selected_metrics else metrics[0].name
        if judge_result and judge_result.best_candidate in metric_by_name:
            chosen_name = judge_result.best_candidate

        chosen_outline = outline_by_name.get(chosen_name, selected_candidates[0])
        logger.info(
            "PM 候选大纲选择完成: selected=%s chosen=%s llm_judge=%s",
            [metric.name for metric in selected_metrics],
            chosen_name,
            bool(judge_result),
        )
        return chosen_outline, selected_candidates, selected_metrics, judge_result

    def generate_outline_once(
        self,
        topic: str,
        retry_note: str = "",
        attempt: int = 1,
    ) -> ContentOutline:
        """只调用一次 PM LLM，用于评估首轮大纲质量或由 plan_content 复用。"""
        system_prompt = (
            "你是一名资深产品经理和内容策划专家。你的任务是根据用户给出的主题，"
            "规划一份结构严谨、逻辑清晰、便于后续调研和写作的深度报告大纲。"
            "请以 JSON 格式返回，字段值中不得使用双引号，用单引号或中文引号代替。"
        )

        user_prompt = self._outline_user_prompt(topic, retry_note)
        with timed_block(logger, f"PM LLM 规划大纲 attempt={attempt}", slow_after=8.0):
            with tracked_call(logger, f"PM LLM 规划大纲 attempt={attempt}", [system_prompt, user_prompt]) as record:
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                record["output_payload"] = response.content
        with timed_block(logger, "解析 PM JSON 输出", slow_after=1.0):
            return parse_llm_json(response.content, ContentOutline)

    def _outline_user_prompt(self, topic: str, retry_note: str = "") -> str:
        """构造大纲规划提示词，避免生成过粗的三段式大纲。"""
        return (
            f"请为以下主题规划一份深度报告大纲：{topic}"
            f"{retry_note}\n\n"
            "大纲要求：\n"
            f"- sections 必须包含 {MIN_OUTLINE_SECTIONS}-{MAX_OUTLINE_SECTIONS} 个主要章节\n"
            "- 章节要便于后续独立调研，避免只给“现状/案例/展望”三段式结构\n"
            "- 大纲应包含明确的结构角色：背景/问题定义、证据或技术基础、案例或场景分析、横向比较或模式归纳、风险挑战、实施建议或结论\n"
            "- 如果主题涉及案例、行业实践或落地应用，应优先按“可独立调研且可核验”的场景拆分，不要为了覆盖行业而机械罗列行业\n"
            "- 案例章节数量建议 2-4 个；如果公开案例可能不足，应设置“证据边界/可验证性/风险限制”类章节承接不确定性\n"
            "- 避免全大纲都是行业列表；需要有比较、归纳、评估或决策框架章节把材料上升为观点\n\n"
            "请严格按照以下 JSON 格式返回，不要添加额外字段：\n"
            "{\n"
            '  "title": "报告标题",\n'
            '  "target_audience": "目标受众描述",\n'
            '  "sections": ["章节1标题", "章节2标题", "章节3标题", "章节4标题", "章节5标题", "章节6标题"],\n'
            '  "key_points": ["核心要点1", "核心要点2", "核心要点3"]\n'
            "}"
        )

def pm_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：产品经理 (Planning) ---")
    logger.info("进入 PM 节点: topic=%s", state["topic"])
    with timed_block(logger, "PM 节点总耗时", slow_after=10.0):
        pm = ProductManager()
        samples = _env_int("PM_OUTLINE_SAMPLES", DEFAULT_OUTLINE_CANDIDATE_SAMPLES)
        top_n = _env_int("PM_OUTLINE_TOP_N", DEFAULT_OUTLINE_TOP_N)
        llm_judge = _env_bool("PM_OUTLINE_LLM_JUDGE", True)
        if samples <= 1:
            outline = pm.plan_content(state["topic"])
            candidates = [outline]
            metrics = [evaluate_outline_quality(outline, name="sample_1")]
            judge_result = None
        else:
            outline, candidates, metrics, judge_result = pm.plan_outline_candidates(
                state["topic"],
                samples=samples,
                top_n=top_n,
                llm_judge=llm_judge,
            )
    logger.info("PM 节点完成: title=%s sections=%d candidates=%d", outline.title, len(outline.sections), len(candidates))
    return {
        "outline": outline,
        "outline_candidates": candidates,
        "outline_candidate_metrics": [metric.to_dict() for metric in metrics],
        "outline_judge": judge_result.model_dump() if judge_result else None,
        "history": [f"PM 规划了大纲：{outline.title}"],
    }


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}
