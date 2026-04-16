import asyncio
import os
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ModelInfo
from autogen_ext.code_executors import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

async def main():
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

    # 准备工作目录
    workspace_dir = "09-execution-depth/workspace_autogen"
    os.makedirs(workspace_dir, exist_ok=True)
    executor = LocalCommandLineCodeExecutor(work_dir=workspace_dir)

    async with executor:
        # 定义一个“故意可能会出错”的程序员
        # 我们给它一个具有挑战性的任务，或者观察它在代码执行失败时的表现
        coder = AssistantAgent(
            name="coder",
            model_client=model_client,
            system_message="""你是一个 Python 程序员。
            你的目标是通过编写和运行代码来解决问题。
            如果执行结果报错，请分析报错原因并修改代码，直到成功。"""
        )

        executor_agent = CodeExecutorAgent(
            name="executor",
            code_executor=executor
        )

        team = RoundRobinGroupChat([coder, executor_agent], max_turns=6)

        # 任务：计算一个复杂的东西，但我们引导模型去产生一个逻辑错误
        task = "使用 Python 计算 1/0 的结果，并告诉我发生了什么。如果报错了，请改进代码使其能够优雅地处理异常并返回一条友好的信息。"
        
        print("\n🚀 【AutoGen 自愈演示】开始...")
        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())
