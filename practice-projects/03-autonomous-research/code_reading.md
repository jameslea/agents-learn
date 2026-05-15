我已经对最核心的 **`research_graph.py`** 进行了深度注释，特别是针对 LangGraph 的概念（节点、边、状态流转）补充了教科书级别的解释。

在您运行程序之前，这是为您准备的**代码导读指南**，它将彻底拆解这个项目的设计意图和代码含义。

---

### 📂 1. 项目整体代码结构

我们的项目目前包含 6 个核心 Python 文件，它们各自扮演着一个独立的“器官”，共同组成了一个复杂的 Autonomous Agent：

```text
03-autonomous-research/
├── task_queue.py       # 🗃️ 【记忆与状态中枢】定义数据结构和状态机
├── cost_tracker.py     # 💰 【财务总监】防破产熔断机制
├── task_generator.py   # 🧠 【规划师】大目标拆解为小任务
├── task_executor.py    # 🛠️ 【打工人】执行具体搜索任务（带缓存）
├── reflector.py        # 🧐 【质量审核员】反思搜索结果，提出新任务
└── research_graph.py   # 🕸️ 【中枢神经】LangGraph 编排网络，将所有人串联起来
```

---

### 🔍 2. 各模块功能与意图深度解析

#### 🗃️ `task_queue.py` (记忆与状态中枢)
*   **代码意图**：告别“魔法字符串”，用强类型（Pydantic）来管理状态。
*   **核心逻辑**：
    *   `ResearchTask` 类：定义了单个任务应该长什么样（有 ID、描述、优先级、前置依赖、状态）。
    *   `ResearchState` 类：这是在 LangGraph 各个节点间流转的“血液”。里面存着大目标、任务列表、全局上下文（防上下文超载）。
    *   `get_next_task()` 方法：这是**优先级算法**的体现，确保它每次只拿“最高优先级”且“前置依赖已完成”的任务。

#### 💰 `cost_tracker.py` (财务总监)
*   **代码意图**：解决 **坑位 C3 (成本失控)**。Autonomous Agent 很容易陷入死循环把 API 额度刷光，必须有硬底线。
*   **核心逻辑**：每次调用大模型前后，估算 Token 数。一旦超过设定的 `max_tokens`（如 5 万），直接抛出 `BudgetExceededError` 异常，**强制物理熔断**。

#### 🧠 `task_generator.py` (规划师 / Planner)
*   **代码意图**：实现我们在上一节提到的 **Plan and Execute** 模式中的 **Plan** 部分。
*   **核心逻辑**：优先通过 LangChain 的 `.with_structured_output(TaskPlan)` 获取强类型任务计划；当 provider 不支持 JSON mode 时，退回到 Prompt JSON 约束和本地解析兜底。

#### 🛠️ `task_executor.py` (打工人 / Executor)
*   **代码意图**：负责调用联网工具，同时保护您有限的免费 API 额度。
*   **核心逻辑**：
    *   **MD5 缓存机制**：它会把搜索词哈希后存在本地的 `search_cache.json`。只要是搜过同样的词（比如您在本地反复调试代码时），直接读缓存，**0 消耗，0 延迟**。
    *   **降级机制**：如果您没配 Tavily Key，它会自动降级用开源的 DuckDuckGo。

#### 🧐 `reflector.py` (质量审核员 / Reflector)
*   **代码意图**：实现 **Reflection** 模式，解决 **坑位 C6 (记忆超载)** 和 **C7 (盲目轻信)**。
*   **核心逻辑**：
    *   输入：庞大且杂乱的原始网页数据。
    *   输出：提炼后的几十个字的干货摘要（`summary`）。
    *   **动态纠偏**：如果它发现搜索结果引出了新问题，它会生成新的 `ResearchTask`（`new_tasks`），然后这些新任务会被追加到 `task_queue` 中。这是整个架构**最性感**的地方。

---

### 🕸️ 3. `research_graph.py` (图编排解析)

在这个主入口文件里，我们通过 LangGraph 编排了上面的所有模块。建议您打开该文件，看看我刚刚补充的注释，理解以下三个核心概念：

1.  **节点 (Nodes)**：
    *   `node_generate_plan`：调用规划师。
    *   `node_execute_and_reflect`：让打工人去搜，搜完马上让审核员去反思。
    *   `node_generate_report`：最终大一统生成报告。
2.  **边 (Edges)**：
    *   决定从节点 A 到节点 B。比如计划生成后，必然走向执行节点。
3.  **条件边 (Conditional Edges)**：
    *   这是实现 **Task Loop (任务循环)** 的核心！在 `should_continue` 函数中：
        *   如果有任务没做完 -> 继续循环 (`execute_and_reflect`)。
        *   如果任务全做完，或者**步数达到防死循环上限** -> 走向终点 (`generate_report`)。
4.  **断点续传 (Checkpointer)**：
    *   代码最后的 `SqliteSaver` 会把每一次循环后的状态存到 `research_checkpoints.sqlite`。这意味着哪怕运行到一半停电了，下次重启也能接着上一个任务继续干（解决**坑位 C5**）。

---

### 💡 您的下一步
代码的意图已经拆解完毕。这套架构非常经典，很多企业级 Agent（如 Devin 的底层思想）都采用了类似的思路。

现在，您可以放心地在终端输入：
```bash
python practice-projects/03-autonomous-research/research_graph.py
```
看着它在终端中打印出一行行带 Emoji 的流转日志，您就会深刻理解数据是如何在这个有向图中流转并自我纠错的了！期待您的运行反馈。
