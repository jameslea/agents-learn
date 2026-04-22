"""
Task 11 - SOP 多 Agent 框架版本 (MetaGPT 设计参考实现)

══════════════════════════════════════════════════════
⚠️  注意：本文件是「学习参考代码」，无法在当前共享虚拟环境中直接运行。
    原因：MetaGPT 0.8.x 对 pandas/numpy/faiss-cpu 等有精确版本锁定，
         与项目其他阶段（LlamaIndex 等）存在不可调和的依赖冲突。
    如需实际运行 SOP 框架演示，请参见：crewai_sop_demo.py
══════════════════════════════════════════════════════

【本文件的核心学习价值】
理解 MetaGPT 的两大设计精髓，这是它与其他框架最本质的区别：

1. 「动作驱动 (Action-driven)」的角色定义：
   每个 Role 只负责执行自己的 Action，Action 是最小可复用单元。

2. 「环境发布/订阅 (Pub/Sub)」的协作机制：
   角色通过 _watch([SomeAction]) 声明自己关心什么事件，
   而不是被人"调用"。当环境中出现 WritePRD 的消息时，
   Engineer 自动被触发 —— 这才是真正的"协作约束"。

   对比：原生版 (sop_agent_native.py) 是 PM() -> engineer() -> reviewer() 的显式调用链，
         而 MetaGPT 版是"PM 发布 PRD -> 环境 -> Engineer 订阅后自动启动"。

【若需独立运行此文件，请使用专用虚拟环境】
  # 1. 创建 Python 3.11 虚拟环境（MetaGPT 不支持 3.12+）
  python3.11 -m venv 11-metagpt-sop/venv_metagpt

  # 2. 安装 MetaGPT（使用国内镜像）
  11-metagpt-sop/venv_metagpt/bin/pip install metagpt==0.8.1 python-dotenv \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

  # 3. 初始化配置（首次运行必须，会生成 ~/.metagpt/config2.yaml）
  11-metagpt-sop/venv_metagpt/bin/metagpt --init-config
  # 然后编辑 ~/.metagpt/config2.yaml，填入 api_key 和 base_url

  # 4. 运行脚本
  11-metagpt-sop/venv_metagpt/bin/python 11-metagpt-sop/metagpt_sop_demo.py
"""
import asyncio
import os
from dotenv import load_dotenv

from metagpt.actions import Action
from metagpt.actions.add_requirement import UserRequirement
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team
from metagpt.config2 import Config
from metagpt.configs.llm_config import LLMConfig

# 从项目 .env 文件加载配置，直接注入到 MetaGPT Config，无需 ~/.metagpt/config2.yaml
load_dotenv()

def build_metagpt_config() -> Config:
    """从环境变量构建 MetaGPT 配置，复用项目 .env 中已有的 DeepSeek 配置。"""
    llm_config = LLMConfig(
        api_type="openai",                              # DeepSeek 兼容 OpenAI 接口
        model=os.getenv("MODEL_NAME", "deepseek-chat"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    config = Config(llm=llm_config)
    return config


# --- 1. 定义动作 (Actions) ---
class WritePRD(Action):
    name: str = "WritePRD"
    async def run(self, requirement: str):
        print(f"\n[Action] 正在分析需求并编写 PRD...")
        prompt = f"你是一个资深产品经理。请根据原始需求编写 PRD。需求：{requirement}"
        rsp = await self._aask(prompt)
        return rsp

class WriteCode(Action):
    name: str = "WriteCode"
    async def run(self, prd: str):
        print(f"\n[Action] 正在根据 PRD 编写代码...")
        prompt = f"你是一个高级软件工程师。请根据 PRD 文档提供完整的 Python 代码。PRD：{prd}"
        rsp = await self._aask(prompt)
        return rsp

class ReviewCode(Action):
    name: str = "ReviewCode"
    async def run(self, code: str):
        print(f"\n[Action] 正在进行代码评审...")
        prompt = f"你是一个技术专家。请评审以下代码并给出改进建议。代码：{code}"
        rsp = await self._aask(prompt)
        return rsp

# --- 2. 定义角色 (Roles) ---
class ProductManager(Role):
    name: str = "Alice (PM)"
    profile: str = "产品经理"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WritePRD])
        # 【关键】PM 监听 UserRequirement —— 这是 team.run_project() 发出消息的 cause_by 类型
        self._watch([UserRequirement])

    async def _act(self) -> Message:
        print(f"\n[{self.name}] 察觉到环境中出现了新需求，开始行动。")
        todo = self.rc.todo  # 获取当前需要执行的 Action
        msg = self.get_memories(k=1)[0] # 获取环境中的最新消息(需求)
        result = await todo.run(msg.content)
        
        # 产出结构化消息到环境，声明 cause_by 是 WritePRD
        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg

class Engineer(Role):
    name: str = "Bob (Engineer)"
    profile: str = "软件工程师"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteCode])
        # 核心协作约束：只有当环境中出现了由 WritePRD 产生的消息时，工程师才会触发行动
        self._watch([WritePRD])

    async def _act(self) -> Message:
        print(f"\n[{self.name}] 察觉到环境中出现了 PRD 文档，开始行动。")
        todo = self.rc.todo
        msg = self.get_memories(k=1)[0] # 获取环境中的 PRD
        result = await todo.run(msg.content)
        
        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg

class Reviewer(Role):
    name: str = "Charlie (Reviewer)"
    profile: str = "代码评审员"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewCode])
        # 核心协作约束：只有当环境中出现了由 WriteCode 产生的消息时，评审员才会触发行动
        self._watch([WriteCode])

    async def _act(self) -> Message:
        print(f"\n[{self.name}] 察觉到环境中出现了新的代码，开始评审。")
        todo = self.rc.todo
        msg = self.get_memories(k=1)[0] # 获取环境中的代码
        result = await todo.run(msg.content)
        
        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg

# --- 3. 运行 SOP 团队环境 ---
async def main():
    idea = "开发一个简单的 Python 脚本，能够抓取指定网页的标题并保存为本地文本文件。"
    print(f"原始需求: {idea}")
    print("="*50)

    # 从 .env 构建 MetaGPT 配置（复用 DeepSeek 配置，无需 ~/.metagpt/config2.yaml）
    config = build_metagpt_config()

    # 初始化团队和环境，传入 config
    team = Team(config=config)
    team.hire(
        [
            ProductManager(),
            Engineer(),
            Reviewer()
        ]
    )
    team.invest(investment=3.0)  # 设置最大预算（美元），控制 API 花费上限

    # 将需求发布到环境，这会自动触发 PM（因为他监听所有 Message）
    team.run_project(idea)

    # 启动团队事件循环 (PM -> 环境 -> Engineer -> 环境 -> Reviewer)
    await team.run(n_round=3)

if __name__ == '__main__':
    asyncio.run(main())
