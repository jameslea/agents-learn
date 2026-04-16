import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()

# ==========================================
# 1. 定义大语言模型 (LLM)
# ==========================================
# CrewAI 1.0+ 推荐使用其内置的 LLM 类，它底层集成了 LiteLLM。
# 这样可以自动适配各种 API 端点并避免 Pydantic 类型冲突。
llm = LLM(
    model=f"openai/{os.getenv('MODEL_NAME', 'deepseek-chat')}",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

# ==========================================
# 2. 定义 Agents (角色扮演)
# ==========================================
# CrewAI 的核心在于 backstory（背景故事）。
# 它通过赋予模型一个强烈的“身份感”来过滤掉不符合职业背景的行为。

researcher = Agent(
    role="资深 AI 趋势研究员",
    goal="寻找 2026 年最前沿的 AI Agent 技术趋势",
    backstory="""你是一名拥有 10 年经验的科技分析师，擅长从琐碎的信息中
    提取出商业价值。你对 LangGraph, CrewAI, AutoGen 等框架有深入的研究。""",
    verbose=True,
    allow_delegation=False, # 禁止将任务外包给别人
    llm=llm
)

writer = Agent(
    role="资深科技自媒体主编",
    goal="根据研究报告写一篇引人入胜的公众号文章内容",
    backstory="""你擅长将深奥的技术术语转化为通俗易懂的“人话”。
    你的文章风格幽默且富有洞察力，深受开发者喜爱。""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# ==========================================
# 3. 定义 Tasks (任务分配)
# ==========================================
# 任务定义了具体要做什么，以及预期的输出格式。

task1 = Task(
    description="调研目前最火的 Agent 框架（如 LangGraph），并总结出 3 个核心卖点。",
    expected_output="一份包含 3 个核心卖点和简单原理解释的研究简报。",
    agent=researcher
)

task2 = Task(
    description="基于研究简报，写一篇适合在朋友圈传播的 300 字短文。",
    expected_output="一篇包含吸引人的标题和正文的短文。",
    agent=writer
)

# ==========================================
# 4. 组建团队并开工 (Crew & Kickoff)
# ==========================================
# Crew 是一个容器，它把员工和任务打包在一起，并规定了合作流程。

tech_crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,  # 顺序执行：研发 -> 写作
    verbose=True
)

if __name__ == "__main__":
    print("\n🚀 【数字编辑部】开始办公...\n")
    result = tech_crew.kickoff()
    
    print("\n" + "="*30)
    print("✨ 最终产出内容:")
    print(result)
    print("="*30)
