import logging
import json
from typing import List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from common.llm_factory import build_llm, resolve_provider_config
from pydantic import BaseModel, Field

# 尝试引入本地类型
try:
    from task_queue import ResearchTask
except ImportError:
    from .task_queue import ResearchTask

logger = logging.getLogger("reflector")

class ReflectionResult(BaseModel):
    """反思结果"""
    is_useful: bool = Field(description="搜索结果是否对完成最终目标有实质性帮助")
    summary: str = Field(description="如果结果有用，提取其中最有价值的信息摘要；如果无用，说明原因")
    new_tasks: List[ResearchTask] = Field(default_factory=list, description="如果发现知识盲区，需要补充的新任务（最多2个）")
    is_goal_achieved: bool = Field(default=False, description="终极目标是否已经达成")


def _parse_reflection_result(result) -> ReflectionResult:
    """兼容原生结构化输出和不支持 JSON mode 的 OpenAI-compatible provider。"""
    if isinstance(result, ReflectionResult):
        return result

    content = getattr(result, "content", result)
    if isinstance(content, ReflectionResult):
        return content
    if not isinstance(content, str):
        return ReflectionResult.model_validate(content)

    try:
        return ReflectionResult.model_validate_json(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return ReflectionResult.model_validate(json.loads(content[start : end + 1]))

class Reflector:
    """
    负责对 Executor 获取的数据进行反思（Reflection）。
    这是解决坑位 C6 (上下文超载) 和 C7 (盲目轻信) 的核心。
    """
    def __init__(self, llm=None):
        from dotenv import load_dotenv
        load_dotenv()

        provider_config = resolve_provider_config()
        if llm is not None:
            self.llm = llm
            self.structured_output = False
        elif provider_config.supports_json_mode:
            self.llm = build_llm(json_mode=True).with_structured_output(ReflectionResult, method="json_mode")
            self.structured_output = True
        else:
            logger.info(
                "Provider %s 不声明支持 JSON mode，Reflector 使用 Prompt JSON + 本地解析兜底。",
                provider_config.name,
            )
            self.llm = build_llm(json_mode=False)
            self.structured_output = False

    def reflect(self, goal: str, task_desc: str, raw_data: str) -> ReflectionResult:
        """
        根据原始目标和当前任务，评估收集到的原始数据。
        """
        logger.info(f"🤔 正在对任务结果进行反思压缩: '{task_desc}'")
        
        # 为了防止上下文超载，如果原始数据太长，强制截断
        # 实际生产中可使用更复杂的切片或总结摘要机制
        if len(raw_data) > 4000:
            raw_data = raw_data[:4000] + "\n...[数据过长，已截断]"
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个苛刻的知识评估官。
团队的终极目标是：{goal}
当前执行的子任务是：{task_desc}

刚才搜索到的原始数据如下：
<data>
{raw_data}
</data>

请评估这些数据：
1. 它是否真能帮助达成终极目标？(is_useful)
2. 过滤掉所有废话、广告，提炼出干货摘要。如果数据全是垃圾，也请直说。(summary)
3. 仔细看数据中是否有尚未解答的疑点？如果有，请提出1-2个新的、更具体的调研任务。(new_tasks)
4. 综合目前获取的数据，是否已经收集了**足够写出一篇专业研报**的核心素材？如果是（无需做到完美无缺），请设为 true。(is_goal_achieved)

你必须输出一个合法的 JSON 对象，包含 "is_useful"(布尔), "summary"(字符串), "new_tasks"(任务对象列表，可为空), "is_goal_achieved"(布尔)。
其中 new_tasks 列表内的每个对象必须包含: "description"(字符串，任务描述), "priority"(数字), "dependencies"(字符串列表)。
"""),
            ("user", "开始反思！")
        ])
        
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({"goal": goal, "task_desc": task_desc, "raw_data": raw_data})
            result = result if self.structured_output else _parse_reflection_result(result)
            if result.is_useful:
                logger.info(f"💡 发现有价值信息: {result.summary[:50]}...")
            else:
                logger.warning(f"🗑️ 数据无用，被抛弃: {result.summary[:50]}...")
                
            for nt in result.new_tasks:
                logger.info(f"➕ 衍生出新任务: {nt.description}")
                
            return result
        except Exception as e:
            logger.error(f"❌ 反思环节失败: {e}")
            return ReflectionResult(is_useful=False, summary="反思过程发生错误，未提取到有效信息。")

# 测试代码
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    reflector = Reflector()
    res = reflector.reflect(
        goal="调研 2026 年 AI Agent 框架",
        task_desc="搜索 LangGraph 与 smolagents 的区别",
        raw_data="LangGraph 强调图架构和持久化，而 smolagents 强调代码沙箱和极致轻量。买鞋子就上淘宝网..."
    )
    print(res)
