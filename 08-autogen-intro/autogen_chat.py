import asyncio
import os
import logging
from dotenv import load_dotenv

# AutoGen 0.4+ 核心组件
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ModelInfo

# 扩展组件：本地代码执行器
from autogen_ext.code_executors import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 配置日志
logging.basicConfig(level=logging.WARNING)

load_dotenv()

async def main():
    # ==========================================
    # 1. 配置模型客户端 (Model Client)
    # ==========================================
    model_client = OpenAIChatCompletionClient(
        model=os.getenv("MODEL_NAME", "deepseek-chat"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="unknown"
        )
    )

    # ==========================================
    # 2. 配置执行环境 (Execution Environment)
    # ==========================================
    # 创建一个本地代码执行器，并指定工作目录
    workspace_dir = "08-autogen-intro/workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    
    # ⚠️ 安全警告：LocalCommandLineCodeExecutor 会在本地真实执行代码。
    # 在生产环境中建议使用 DockerCommandLineCodeExecutor。
    executor = LocalCommandLineCodeExecutor(work_dir=workspace_dir)

    # ==========================================
    # 3. 定义团队 (Agents & Team)
    # ==========================================
    async with executor:
        # 负责写代码的智能体
        coder = AssistantAgent(
            name="coder",
            model_client=model_client,
            system_message="""你是一个顶尖的 Python 程序员。
            你的任务是编写 Python 代码来解决用户提出的问题。
            请确保你的代码包含必要的打印输出，以便执行者能够返回结果。
            代码块必须使用标准 markdown 格式。"""
        )

        # 负责执行代码的智能体（它不思考，只负责跑 coder 给出的代码块）
        executor_agent = CodeExecutorAgent(
            name="executor",
            code_executor=executor
        )

        # 组建团队：采用轮询模式对话
        # 团队目标：直到任务解决为止
        team = RoundRobinGroupChat(
            participants=[coder, executor_agent], 
            max_turns=10
        )

        # ==========================================
        # 4. 运行并演示
        # ==========================================
        task = "编写 Python 代码找出第 5 个素数是多少（包含 2）。"
        
        print(f"\n🚀 【AutoGen 代码协作流】正式启动！")
        print(f"任务目标: {task}\n")

        # 使用 Console UI 助手实时在终端展示对话和执行流
        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())
