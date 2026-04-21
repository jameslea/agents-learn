import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 1. 配置加载
load_dotenv()

# 2. 模拟软件团队的角色定义
class SOPTeam:
    def __init__(self):
        model_name = os.getenv("MODEL_NAME", "deepseek-chat")
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_BASE_URL")
        
        self.llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.1
        )

    async def product_manager_action(self, requirement: str) -> str:
        """产品经理角色：将原始需求转为 PRD 文档"""
        print("\n[Role: Product Manager] 正在分析需求并编写 PRD...")
        prompt = ChatPromptTemplate.from_template(
            "你是一个资深产品经理。请根据以下原始需求，编写一份结构化的 PRD 文档。\n"
            "PRD 应包含：目标、核心功能点、用户故事、非功能性需求。\n"
            "原始需求：{requirement}\n"
            "输出格式：Markdown"
        )
        chain = prompt | self.llm
        result = await chain.ainvoke({"requirement": requirement})
        return result.content

    async def engineer_action(self, prd: str) -> str:
        """工程师角色：根据 PRD 编写代码实现"""
        print("\n[Role: Engineer] 正在根据 PRD 编写代码...")
        prompt = ChatPromptTemplate.from_template(
            "你是一个高级软件工程师。请根据以下 PRD 文档，提供完整的 Python 代码实现。\n"
            "PRD 文档：{prd}\n"
            "输出要求：仅输出代码块，包含必要的注释。"
        )
        chain = prompt | self.llm
        result = await chain.ainvoke({"prd": prd})
        return result.content

    async def reviewer_action(self, code: str) -> str:
        """评审员角色：对代码进行安全和质量评审"""
        print("\n[Role: Reviewer] 正在进行代码评审...")
        prompt = ChatPromptTemplate.from_template(
            "你是一个技术专家和安全审计员。请评审以下代码，指出潜在的问题、漏洞或性能优化建议。\n"
            "代码：{code}\n"
            "输出格式：Markdown 列表"
        )
        chain = prompt | self.llm
        result = await chain.ainvoke({"code": code})
        return result.content

# 3. 运行主 SOP 流程
async def run_sop_workflow(user_requirement: str):
    team = SOPTeam()
    
    print("="*50)
    print(f"原始需求: {user_requirement}")
    print("="*50)

    # 步骤 1: 需求 -> PRD
    prd = await team.product_manager_action(user_requirement)
    print("\n--- PRD 产出 ---")
    print(prd[:300] + "...")

    # 步骤 2: PRD -> Code
    code = await team.engineer_action(prd)
    print("\n--- Code 产出 ---")
    print(code[:300] + "...")

    # 步骤 3: Code -> Review
    review = await team.reviewer_action(code)
    print("\n--- Review 报告 ---")
    print(review)

    print("\n" + "="*50)
    print("SOP 流程结束：已产出结构化文档链。")

if __name__ == "__main__":
    demo_requirement = "开发一个简单的 Python 脚本，能够抓取指定网页的标题并保存为本地文本文件。"
    asyncio.run(run_sop_workflow(demo_requirement))
