import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchTask(BaseModel):
    """
    单个调研子任务的定义。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = Field(..., description="任务的详细描述，例如'搜索并总结 2026 年最新的多智能体框架'")
    priority: int = Field(default=1, description="优先级，数字越小优先级越高 (1 为最高)")
    dependencies: List[str] = Field(default_factory=list, description="前置任务的 ID 列表")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    result: Optional[str] = Field(default=None, description="任务执行后的摘要或结果")
    
class ResearchState(BaseModel):
    """
    LangGraph 中的全局状态对象。强类型约束避免魔法字符串。
    解决宕机状态丢失 (C5) 的前提。
    """
    original_goal: str = Field(..., description="用户最初设定的宏大目标，用于防止目标漂移 (C1)")
    tasks: List[ResearchTask] = Field(default_factory=list, description="任务列表")
    completed_steps: int = Field(default=0, description="已执行的步骤数，用于防止无限循环 (C2)")
    max_steps: int = Field(default=15, description="最大允许执行的步数")
    final_report: Optional[str] = Field(default=None, description="最终生成的调研报告")
    
    # 全局搜集到的知识上下文，需配合摘要机制防止上下文超载 (C6)
    context_memory: str = Field(default="", description="已提炼的全局上下文记忆")

    def get_next_task(self) -> Optional[ResearchTask]:
        """
        获取下一个可执行的任务 (状态为 TODO 且没有未完成的依赖)。
        解决优先级混乱 (C4) 的第一步。
        """
        # 提取所有已完成任务的 ID
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        
        available_tasks = []
        for task in self.tasks:
            if task.status == TaskStatus.TODO:
                # 检查依赖是否全部满足
                if all(dep in completed_ids for dep in task.dependencies):
                    available_tasks.append(task)
                    
        if not available_tasks:
            return None
            
        # 按优先级排序，数字小的排前面
        available_tasks.sort(key=lambda x: x.priority)
        return available_tasks[0]
