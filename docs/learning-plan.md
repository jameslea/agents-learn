# AI Agents 项目实战路线图 (Tutorial Roadmap)

> 目标读者：具备基础 LLM API 调用经验，希望系统学习智能体架构的开发者
> 本文档定义了 `agents-learn` 仓库中代码示例的递进逻辑。

## 一、教程目标

通过系统学习，理解 AI Agent 的核心概念、关键组成部分、主流架构模式，并能够使用 LangChain/LangGraph 独立构建多步骤、多 Agent 协作的实战系统。

具体目标：

- **A) 个人任务自动化** — 让 AI 自动完成复杂多步骤任务（搜索 → 分析 → 报告）
- **C) 深入理解 Agent 架构** — 掌握 Planning / Memory / Tools / Action 的实现原理
- **D) 多 Agent 协作** — 理解并实现多个 Agent 分工合作

## 二、学习风格

实践优先，边做边理解原理。与 skills 学习计划风格一致。

## 三、学习路径（五阶段）

```
阶段一：Agent 核心概念与架构思维
阶段二：LangChain 工具调用 + 记忆系统
阶段三：规划与推理模式 ReAct/CoT
阶段四：多 Agent 协作架构
阶段五：生产级 Self-RAG 项目实战
进阶篇（多框架横向实验室）：
  阶段六：smolagents (代码驱动智能体)
  阶段七：CrewAI (职场角色扮演与 SOP 工作流)
  阶段八：AutoGen (对话式驱动与环境自愈)
  阶段九：执行机制深度对比 (AST 模拟 vs 物理环境)
```

---

## 四、详细阶段计划

### 阶段一：Agent 核心概念（1-2 天）

**目标**：建立 Agent 的整体认知框架，理解核心术语。

**内容**：

1. **什么是 Agent**
   - 单次响应 vs 自主多步执行的区别
   - Claude Code 就是一个 Agent：感知 → 推理 → 行动的循环
   - Agent = LLM + 工具 + 记忆 + 规划

2. **Agent 核心四块积木**
   ```
   Planning（规划）  — 把复杂任务拆解成步骤
   Memory（记忆）   — 跨对话保持上下文
   Tools（工具）   — 调用外部系统（搜索/API/代码）
   Action（行动）  — 执行决策并影响外部世界
   ```

3. **Agent 与 Skill 的对比理解**
   | 维度 | Skill | Agent |
   |------|-------|-------|
   | 本质 | 注入系统提示的指令片段 | 自主循环执行单元 |
   | 触发 | description 自动匹配 | LLM 推理决定下一步 |
   | 组合 | 多个 Skill 可叠加 | 多 Agent 协作 |
   | 持久化 | 文件系统 | 向量数据库 |

4. **经典案例分析**
   - 为什么 GPT-4 本身不是 Agent
   - 为什么 Claude Code 是 Agent
   - AutoGPT 的工作原理（ReAct 模式）

**行动**：
- 阅读 LangChain 官方文档中 Agent 章节（约 1 小时）
- 在本地用 `pip install langchain langchain-openai` 搭一个最小 demo

**验收标准**：能用自己的话解释"什么是 Agent，它和普通 LLM 调用的本质区别是什么"。

---

### 阶段二：工具调用 + 记忆系统（3-5 天）

**目标**：掌握 LangChain 工具调用的工作机制，理解对话记忆的实现方式。

**内容**：

1. **工具调用机制**
   - LangChain Tool 类的定义方式
   - `@tool` 装饰器写法
   - ToolChoice 模式：LLM 如何决定调用哪个工具
   - 多工具协同：Parallel / Sequential 调用

2. **实战：研究助手 Agent**
   ```
   用户输入一个主题
       ↓
   Agent 搜索网页（SerpAPI / DuckDuckGo）
       ↓
   总结关键信息（LLM）
       ↓
   保存结果到本地文件
       ↓
   用户获得完整报告
   ```

3. **记忆系统**
   - 对话历史（ConversationBufferMemory）
   - 向量记忆（VectorStoreMemory）— Embeddings + FAISS/Chroma
   - 记忆的检索与注入时机

4. **实战：给研究助手加记忆**
   - 同一对话中跨多轮记住上下文
   - 新对话中召回历史关键信息

**行动**：
- 用 LangChain 实现一个带搜索 + 总结 + 记忆的个人研究助手
- 对比 `ConversationBufferMemory` 和 `VectorStoreMemory` 的效果差异

**验收标准**：Agent 能完成"搜索 → 总结 → 存档"三步骤，并在多轮对话中保持记忆。

---

### 阶段三：规划与推理模式（2-3 天）

**目标**：理解 ReAct 和 CoT 模式，理解 LangGraph 状态机的工作方式。

**内容**：

1. **Chain-of-Thought（CoT）**
   - 让 LLM 显式输出推理步骤
   - Zero-shot CoT vs Few-shot CoT

2. **ReAct 模式**
   ```
   Thought（思考）→ Action（行动）→ Observation（观察）→ 循环
   ```
   - ReAct 是 AutoGPT 的核心技术
   - LangChain Agent 的 ReAct 实现

3. **LangGraph 状态机**
   - 状态（State）+ 节点（Node）+ 边（Edge）
   - 条件边：Agent 根据状态决定下一步
   - 实战：用 LangGraph 重构研究助手，加入条件分支

4. **实战：多步决策 Agent**
   - 根据上一步结果决定下一步行动
   - 错误处理：工具调用失败时 Agent 如何恢复

**行动**：
- 用 LangGraph 实现一个带 ReAct 循环的 Agent，支持条件分支
- 在 LangGraph 中加入错误重试逻辑

**验收标准**：Agent 能自主完成 5 步以上的复杂任务，且中途失败能恢复重试。

---

### 阶段四：多 Agent 协作（2-3 天）

**目标**：理解多 Agent 架构模式，能够设计与实现多个 Agent 的协作流程。

**内容**：

1. **多 Agent 协作的本质**
   - 角色定义（Role）+ 任务分配（Task）+ 消息传递（Message）
   - 为什么多个专业 Agent 比一个全能 Agent 更可靠

2. **CrewAI 入门**
   - Agent / Task / Crew 的概念
   - 给 Agent 定义角色和目标
   - 定义任务依赖关系（DAG）

3. **LangGraph 多 Agent**
   - Supervisor 模式：一个 Agent 调度其他 Agent
   - 去中心化模式：Agent 间点对点消息

4. **实战：研究团队 Agent**
   ```
   Supervisor Agent
   ├── Researcher Agent（搜索 + 信息提取）
   ├── Analyst Agent（数据分析 + 图表）
   └── Writer Agent（生成报告）
   ```

**行动**：
- 用 CrewAI 或 LangGraph 实现一个 3 Agent 协作系统
- Agent 之间有明确角色分工和任务传递

**验收标准**：能实现"一个复杂任务 → 多个专业 Agent 分工 → 汇总输出"的完整流程。

---

### 阶段五：生产级 Self-RAG 项目实战（3-5 天）

**目标**：独立完成一个完整项目，掌握复杂图架构和可观测性组件。

**内容**：

1. **Self-RAG 闭环设计**
   - 包含检索、质量评分、网络搜索兜底和最终生成的复杂 DAG。
2. **生产级架构升级**
   - 弃用魔法字符串，使用 Pydantic BaseModel 与 Enum 实现强类型状态流转。
3. **可观测性 (Observability)**
   - 集成 Langfuse，实现全链路 Trace 追踪与耗时成本评估。

**行动**：
- 在 `05-final-project` 中完成基于 LangGraph 的端到端 Self-RAG 助手。

---

### 进阶篇：多框架横向实验室（1 周）

**目标**：打破单框架认知，横评业界最主流的四大 Agent 框架，建立全面的技术选型视角。

**内容**：

1. **阶段六：smolagents**
   - 体验 HuggingFace 出品的极简框架。
   - 核心范式：Code-as-Actions（代码即操作），直接驱动底层 AST 执行。
2. **阶段七：CrewAI**
   - 体验基于 Role-playing 的职场化协作框架。
   - 核心范式：为 Agent 撰写 Backstory（背景故事），以任务队列流水线驱动进度。
3. **阶段八：AutoGen**
   - 体验微软开源的现象级多智能体框架。
   - 核心范式：Conversational（对话驱动），让写代码与执行代码的 Agent 进行左右互搏与报错自愈。
4. **阶段九：机制深度挖掘**
   - 横向对比：“AST 内存模拟”与“OS 子进程隔离”在代码执行及安全性上的根本差异。

**行动**：
- 分别使用各大框架实现一遍“工具调用+代码计算”的基础流程。
- 阅读项目的 `AGENTS_KNOWLEDGE_MAP.md`，深度消化各框架的选型边界。

**验收标准**：能够清晰说出若接到一个新的业务需求，应当选用 LangGraph / CrewAI 还是 AutoGen。

---

## 五、核心参考资源

| 资源 | 说明 |
|------|------|
| [LangChain 官方文档](https://python.langchain.com/docs) | 首选，覆盖所有概念 |
| [LangGraph 文档](https://langchain-ai.github.io/langgraph/) | 状态机模式核心 |
| [CrewAI 文档](https://docs.crewai.com) | 多 Agent 入门 |
| [smolagents 文档](https://huggingface.github.io/smolagents/) | 轻量 Agent 框架 |
| [LangChain Agents 概念](https://python.langchain.com/docs/concepts/agents) | Agent 核心概念 |

---

## 六、与 skills 学习计划的对照

| 学习维度 | skills 计划 | agents 计划 |
|---------|-----------|------------|
| 核心单元 | Skill（指令片段） | Agent（自主执行单元）|
| 触发机制 | description 自动匹配 | LLM 推理决定行动 |
| 组合方式 | 多个 Skill 可叠加 | 多 Agent 协作 |
| 持久化 | 文件系统 | 向量数据库 |
| 评估方式 | /context token 审计 | trace 可视化 |

---



