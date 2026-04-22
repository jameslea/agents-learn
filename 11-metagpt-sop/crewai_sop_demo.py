"""
Task 11 - SOP 多 Agent 框架版本 (CrewAI 可运行实现)

══════════════════════════════════════════════════════
✅  本文件可在当前虚拟环境中直接运行（CrewAI 已在 phase07 中安装）
    参考学习：metagpt_sop_demo.py 展示了 MetaGPT 的事件驱动设计思想
══════════════════════════════════════════════════════

【与原生版本的核心区别】
  原生版 (sop_agent_native.py):
    - 手动拼接 Prompt 字符串
    - 用函数返回值直接传递给下一个函数（PM 返回 PRD → 传入 engineer_action(prd)）
    - 相当于写了 3 个独立函数并顺序调用

  CrewAI 框架版 (本文件):
    - Agent 定义自己的 role / goal / backstory，框架自动构建 System Prompt
    - Task 通过 context=[上一个Task] 声明依赖，框架自动传递上游输出
    - Crew 统一编排，开发者只关心"谁做什么"，不关心"怎么传数据"

【运行方式】
  source venv/bin/activate
  python 11-metagpt-sop/crewai_sop_demo.py
"""
import os
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()

# --- 1. 配置 LLM ---
# CrewAI 0.100+ 内部使用 litellm，需要用 crewai.LLM 来配置
# 对于 DeepSeek 等兼容 OpenAI 接口的服务，格式为 "openai/<模型名>"
llm = LLM(
    model=f"openai/{os.getenv('MODEL_NAME', 'deepseek-chat')}",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.1
)

# --- 2. 定义 Agents（角色）---
# 框架会将 role + goal + backstory 自动注入为角色的 System Prompt
# 你只需要声明"这个角色是谁、想做什么"，不需要手写 Prompt 模板
product_manager = Agent(
    role="产品经理",
    goal="将模糊的用户需求，转化为清晰、结构化的 PRD（产品需求文档）",
    backstory=(
        "你是一位拥有 10 年经验的资深产品经理，擅长将用户需求分解为可执行的功能点。"
        "你的 PRD 结构清晰，总是包含：目标、核心功能点、用户故事和非功能性需求。"
    ),
    llm=llm,
    verbose=True
)

engineer = Agent(
    role="高级软件工程师",
    goal="根据 PRD 文档，编写高质量的 Python 代码实现",
    backstory=(
        "你是一位精通 Python 的高级软件工程师，代码简洁、注释清晰、遵循 PEP8 规范。"
        "你只输出代码，不做额外解释。"
    ),
    llm=llm,
    verbose=True
)

code_reviewer = Agent(
    role="技术评审员",
    goal="对工程师提交的代码进行全面的质量和安全评审",
    backstory=(
        "你是一位经验丰富的技术专家，专注于代码质量、安全漏洞和性能优化。"
        "你的评审报告以 Markdown 格式输出，清晰列出每个问题和对应的改进建议。"
    ),
    llm=llm,
    verbose=True
)

# --- 3. 定义 Tasks（任务）---
# 【核心 SOP 约束】: context 参数声明任务间依赖
# 框架确保 engineer_task 必须等 prd_task 完成后才能执行，且自动传入 PRD 内容
user_requirement = "开发一个简单的 Python 脚本，能够抓取指定网页的标题并保存为本地文本文件。"

prd_task = Task(
    description=f"根据以下原始需求，编写一份完整的 PRD 文档（Markdown 格式）。\n原始需求：{user_requirement}",
    expected_output="一份结构化的 PRD 文档，包含：目标、核心功能点、用户故事、非功能性需求。",
    agent=product_manager
)

engineer_task = Task(
    description="根据 PRD 文档，编写完整的 Python 代码实现。代码需要能直接运行。",
    expected_output="一份完整的 Python 代码，包含必要的注释，可以直接运行。",
    agent=engineer,
    context=[prd_task]  # SOP 约束：依赖 PRD 产出，框架自动将 prd_task 的结果传入
)

review_task = Task(
    description="对工程师提交的代码进行全面评审，指出潜在问题、漏洞和优化建议。",
    expected_output="一份 Markdown 格式的代码评审报告，包含：问题列表、严重程度、改进建议。",
    agent=code_reviewer,
    context=[engineer_task]  # SOP 约束：依赖代码产出，框架自动传入
)

# --- 4. 组建 Crew 并启动 ---
# Process.sequential = 严格的 SOP 顺序执行（产品经理 -> 工程师 -> 评审员）
crew = Crew(
    agents=[product_manager, engineer, code_reviewer],
    tasks=[prd_task, engineer_task, review_task],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("=" * 55)
    print("  启动 CrewAI SOP 软件团队流程")
    print("  需求 -> PRD -> 代码 -> 评审报告")
    print("=" * 55)
    result = crew.kickoff()
    print("\n\n" + "=" * 55)
    print("  SOP 流程完成 - 最终评审报告")
    print("=" * 55)
    print(result)
