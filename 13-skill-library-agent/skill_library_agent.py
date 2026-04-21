import asyncio
import json
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 1. 技能模型定义
class Skill(BaseModel):
    name: str = Field(description="技能名称，使用下划线命名")
    description: str = Field(description="详细描述这个技能是解决什么问题的")
    code_snippet: str = Field(description="该技能的核心 Python 代码或逻辑步骤")

# 2. 技能库 Agent
class SkillLibraryAgent:
    def __init__(self, library_path: str = "13-skill-library-agent/skills.json"):
        load_dotenv()
        self.library_path = library_path
        self.skills: Dict[str, Skill] = self._load_library()
        
        model_name = os.getenv("MODEL_NAME", "deepseek-chat")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1
        )

    def _load_library(self) -> Dict[str, Skill]:
        if not os.path.exists(self.library_path):
            return {}
        with open(self.library_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {name: Skill(**content) for name, content in data.items()}

    def _save_library(self):
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump({name: s.model_dump() for name, s in self.skills.items()}, f, ensure_ascii=False, indent=2)

    def retrieve_relevant_skills(self, task: str) -> List[Skill]:
        """模拟向量检索：根据关键词寻找相关技能"""
        relevant = []
        for skill in self.skills.values():
            # 简化逻辑：如果在任务描述中发现了技能关键字
            if any(word in task.lower() for word in skill.name.split('_')):
                relevant.append(skill)
        return relevant

    async def run_task(self, task: str):
        print(f"\n[任务启动] {task}")
        
        # 1. 检索技能
        existing_skills = self.retrieve_relevant_skills(task)
        skills_context = ""
        if existing_skills:
            print(f"[检索] 发现 {len(existing_skills)} 个相关技能: {[s.name for s in existing_skills]}")
            skills_context = "\n".join([f"技能 {s.name}: {s.description}\n参考逻辑:\n{s.code_snippet}" for s in existing_skills])
        else:
            print("[检索] 未发现匹配技能，将进行初次探索。")

        # 2. 执行任务
        prompt = ChatPromptTemplate.from_template(
            "你是一个拥有长期记忆的智能体。\n"
            "已知技能库：\n{skills_context}\n\n"
            "当前任务：{task}\n"
            "请完成任务。如果你使用了新的逻辑，请在最后以 'NEW_SKILL_FOUND: ...' 的格式总结这个技能。"
        )
        
        chain = prompt | self.llm
        response = await chain.ainvoke({"skills_context": skills_context, "task": task})
        content = response.content
        print(f"\n--- 执行结果 ---\n{content}\n")

        # 3. 学习新技能 (沉淀)
        if "NEW_SKILL_FOUND:" in content:
            new_skill_data = content.split("NEW_SKILL_FOUND:")[1].strip()
            # 简单模拟：让 LLM 将这段描述转化为标准的 Skill 对象
            await self._learn_from_text(new_skill_data)

    async def _learn_from_text(self, text: str):
        print("[学习] 正在将新经验沉淀为技能...")
        prompt = ChatPromptTemplate.from_template(
            "请根据以下描述，提取出一个标准的技能模型（JSON 格式）。\n"
            "描述：{text}\n"
            "字段要求：name, description, code_snippet\n"
            "注意：仅输出 JSON。"
        )
        response = await self.llm.ainvoke(prompt.format(text=text))
        try:
            # 清理可能存在的 Markdown 代码块标记
            clean_content = response.content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:-3]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:-3]
                
            skill_dict = json.loads(clean_content)
            new_skill = Skill(**skill_dict)
            self.skills[new_skill.name] = new_skill
            self._save_library()
            print(f"[成功] 已沉淀新技能: {new_skill.name}")
        except Exception as e:
            print(f"[失败] 技能沉淀解析出错: {e}")

# 4. 演示运行
async def main():
    agent = SkillLibraryAgent()
    
    # 第一次运行：一个全新的任务
    print("===== 第一次运行（探索） =====")
    await agent.run_task("编写一个 Python 函数，计算斐波那契数列的第 n 项。")

    # 第二次运行：类似的或相关的任务
    print("\n===== 第二次运行（复用） =====")
    await agent.run_task("利用斐波那契技能，计算前 10 项的和。")

if __name__ == "__main__":
    asyncio.run(main())
