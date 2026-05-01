import asyncio
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# 1. 数据模型定义
class Task(BaseModel):
    id: int = Field(description="任务唯一标识符")
    name: str = Field(description="任务名称或简短描述")
    description: str = Field(description="任务的具体执行指令")

class TaskList(BaseModel):
    tasks: List[Task] = Field(description="任务列表")

# 2. 核心系统类
class AutonomousTaskAgent:
    def __init__(self, goal: str, max_iterations: int = 5):
        load_dotenv()
        self.goal = goal
        self.max_iterations = max_iterations
        self.tasks: List[Task] = []
        self.completed_tasks: List[Dict] = []
        self.iteration = 0
        
        # 初始化模型
        model_name = os.getenv("MODEL_NAME", "deepseek-v4-flash")
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_BASE_URL")
        
        self.llm = build_llm(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2,
        )

    async def init_tasks(self):
        """根据目标生成初始任务列表"""
        print(f"\n[系统] 正在为目标生成初始任务: {self.goal}")
        
        parser = PydanticOutputParser(pydantic_object=TaskList)
        prompt = ChatPromptTemplate.from_template(
            "你是一个任务规划专家。用户目标是：{goal}\n"
            "请将该目标拆解为 2-3 个初始的关键步骤任务。\n"
            "{format_instructions}"
        )
        
        chain = prompt | self.llm | parser
        result = await chain.ainvoke({
            "goal": self.goal,
            "format_instructions": parser.get_format_instructions()
        })
        self.tasks = result.tasks
        self._print_task_list()

    async def execute_task(self, task: Task):
        """执行单个任务"""
        print(f"\n>>> 正在执行任务 #{task.id}: {task.name}")
        
        prompt = ChatPromptTemplate.from_template(
            "你是一个执行者。你的目标是：{goal}\n"
            "当前任务名称：{task_name}\n"
            "任务详细描述：{task_description}\n"
            "请执行该任务并给出详细结果。如果需要模拟工具调用（如搜索、计算），直接在回答中描述结果即可。"
        )
        
        chain = prompt | self.llm
        result = await chain.ainvoke({
            "goal": self.goal,
            "task_name": task.name,
            "task_description": task.description
        })
        
        execution_result = result.content
        self.completed_tasks.append({
            "task": task.dict(),
            "result": execution_result
        })
        print(f"--- 执行结果 ---\n{execution_result[:200]}...")
        return execution_result

    async def update_tasks(self, last_result: str):
        """根据上一个任务的结果更新或生成新任务"""
        print("\n[系统] 正在根据执行结果分析后续任务...")
        
        parser = PydanticOutputParser(pydantic_object=TaskList)
        prompt = ChatPromptTemplate.from_template(
            "你是一个任务管理专家。用户目标是：{goal}\n"
            "已完成的任务记录：{history}\n"
            "当前任务列表：{current_tasks}\n"
            "上一个任务的执行结果：{last_result}\n\n"
            "请判断是否需要增加新任务。如果目标已接近达成，可以不增加。\n"
            "返回更新后的完整待办任务列表（排除已完成的）。\n"
            "{format_instructions}"
        )
        
        history_str = json.dumps(self.completed_tasks, ensure_ascii=False)
        current_tasks_str = json.dumps([t.dict() for t in self.tasks], ensure_ascii=False)
        
        chain = prompt | self.llm | parser
        result = await chain.ainvoke({
            "goal": self.goal,
            "history": history_str,
            "current_tasks": current_tasks_str,
            "last_result": last_result,
            "format_instructions": parser.get_format_instructions()
        })
        self.tasks = result.tasks
        self._print_task_list()

    def _print_task_list(self):
        if not self.tasks:
            print("[队列] 待办任务列表为空。")
            return
        print("[队列] 当前待办任务:")
        for t in self.tasks:
            print(f"  - [{t.id}] {t.name}")

    async def run(self):
        """主循环"""
        await self.init_tasks()
        
        while self.tasks and self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n\n===== 迭代周期 {self.iteration} / {self.max_iterations} =====")
            
            # 1. 取出任务 (BabyAGI 模式通常取出第一个)
            current_task = self.tasks.pop(0)
            
            # 2. 执行任务
            result = await self.execute_task(current_task)
            
            # 3. 反思与更新
            await self.update_tasks(result)
            
            # 可选：Human-in-the-loop
            # input("按回车继续下一个任务...")
            
        print("\n\n" + "="*50)
        if not self.tasks:
            print("目标完成！所有任务已处理完毕。")
        else:
            print("达到最大迭代次数，停止运行。")
        
        print("\n最终总结报告:")
        # 简单让 LLM 汇总结果
        summary_prompt = ChatPromptTemplate.from_template(
            "目标：{goal}\n执行过程：{history}\n请根据以上执行过程给出最终的总结报告。"
        )
        summary_chain = summary_prompt | self.llm
        summary = await summary_chain.ainvoke({
            "goal": self.goal,
            "history": json.dumps(self.completed_tasks, ensure_ascii=False)
        })
        print(summary.content)

# 3. 运行示例
if __name__ == "__main__":
    # 可以通过环境变量自定义目标
    my_goal = os.getenv("AUTONOMOUS_GOAL", "调研 2024 年最流行的 3 个大语言模型框架，并对比它们的优缺点。")
    
    agent = AutonomousTaskAgent(goal=my_goal)
    asyncio.run(agent.run())
