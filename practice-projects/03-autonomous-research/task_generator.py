import logging
import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 尝试从本项目中引入
try:
    from task_queue import ResearchTask
except ImportError:
    from .task_queue import ResearchTask

logger = logging.getLogger("task_generator")

class TaskPlan(BaseModel):
    """用于大模型输出结构化的任务计划"""
    tasks: List[ResearchTask] = Field(description="为达成目标所需要执行的子任务列表")

class TaskGenerator:
    """
    负责将用户最初的宏大目标拆解为 3-5 个可执行的子任务。
    并赋予合理的依赖关系和优先级。
    """
    def __init__(self, llm=None):
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        # 默认使用 DeepSeek
        self.llm = llm or ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-v4-flash"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        ).with_structured_output(TaskPlan, method="json_mode")

    def generate_initial_tasks(self, goal: str) -> List[ResearchTask]:
        """
        根据宏大目标，生成初始任务。
        """
        logger.info(f"🧠 正在为目标生成初始调研任务: {goal}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个经验丰富的首席研究员。
用户的宏大目标是：{goal}

请将这个目标拆解为 3 到 5 个明确、可执行的联网搜索子任务。
要求：
1. 任务必须足够具体，可以直接放入搜索引擎。
2. 为任务设置依赖关系（有些信息必须先查到，才能查后续信息）。
3. 为任务设置优先级（1 为最高，数字越小越先执行）。
4. 不要生成超过 5 个任务，保持聚焦。

你必须输出一个合法的 JSON 对象，包含一个 "tasks" 列表，列表中每个对象必须包含 description, priority, 和 dependencies(字符串列表)。
"""),
            ("user", "开始拆解！")
        ])
        
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({"goal": goal})
            tasks = result.tasks
            logger.info(f"✅ 成功拆解出 {len(tasks)} 个子任务")
            for t in tasks:
                logger.info(f"  - [优先级 {t.priority}] {t.description}")
            return tasks
        except Exception as e:
            logger.error(f"❌ 任务生成失败: {e}")
            # 返回一个保底的单一任务
            return [ResearchTask(description=f"搜索：{goal}", priority=1)]

# 测试代码
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    generator = TaskGenerator()
    tasks = generator.generate_initial_tasks("深度调研 2026 年 AI Agent 编程框架的竞争格局")
