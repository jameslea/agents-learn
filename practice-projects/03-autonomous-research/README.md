# 项目 C：自主调研助手 (Autonomous Research Assistant)

## 场景描述
用户给定一个模糊或宏大的长期目标（例如："深度调研 2026 年 AI Agent 编程框架的竞争格局"）。Agent 将像人类研究员一样，自主拆解子任务、调度执行（联网搜索）、反思结果，并动态更新后续计划，最终输出一份结构化的深度调研报告。

## 技术栈
- **LangGraph**：构建任务循环图（Task Loop）及带状态的有向图 (`GraphState`)。
- **Pydantic**：任务强类型管理与状态机抽象。
- **Tavily / DuckDuckGo**：外部联网搜索能力，支持本地 MD5 结果缓存。
- **SQLite Checkpointer**：断点续传与持久化，保障宕机不丢进度，支持多 Thread ID 并发任务。

## 坑位地图与当前进度
| 编号 | 坑 | 现象 | 根因 | 方案 | 状态 |
|------|-----|------|------|------|------|
| C1 | 目标漂移 | Agent 跑着跑着忘了最初要干什么 | 任务拆解偏离主线 / Context 遗忘 | 在每次反思时强制注入 `original_goal`，并在 `GraphState` 中严格维护类型 | ✅ |
| C2 | 无限循环 | 一直创建新任务，永不停机 | 缺少强制终止条件和闭环判定 | 引入 `is_goal_achieved` 提前终止机制，及接近 `max_steps` 时的禁止衍生机制 | ✅ |
| C3 | 成本失控 | 一次调研消耗数万 Token | 未设置预算监控和熔断机制 | 引入 `TokenBudgetTracker`，设定 Token 上限，超限自动熔断保护 | ✅ |
| C4 | 优先级混乱 | 先查边缘信息，核心问题放后面 | 缺少优先级算法 | Reflector 动态调整 `priority`，TODO 列表按优先级排序 | ✅ |
| C5 | 执行中途宕机 | 重启后状态丢失或重复执行任务 | 缺少持久化（Checkpoint） | 引入 `SqliteSaver`，通过参数动态传入 `thread_id` 实现断点续传 | ✅ |
| C6 | 上下文超载 | 结果塞爆上下文，导致后续变傻 | 缺少数据压缩 / 摘要节点 | Reflector 提取精简 `summary` 追加到上下文，抛弃无用数据 | ✅ |
| C7 | 盲目轻信 | 搜出垃圾信息直接采纳，影响质量 | 缺少结果评估（Reflector） | Reflector 增加 `is_useful` 校验，无用信息直接打回并记录 | ✅ |

## 运行方式
确保已经配置 `.env` 并在虚拟环境中安装了依赖。

```bash
# 运行默认任务（thread_id 默认为 research_demo_01）
python practice-projects/03-autonomous-research/research_graph.py

# 开启独立的新任务，或从崩溃中恢复该任务
python practice-projects/03-autonomous-research/research_graph.py my_custom_task_01
```

## 踩坑记录
1. **Pydantic 验证错误与大模型输出不一致**
   - **现象**：`Reflector` 返回的 JSON 键是 `task`，但 Pydantic 模型需要 `description`，导致 Pydantic 严重验证报错。
   - **解决**：在 Prompt 中必须显式、逐字段地提供合法的 JSON Schema 要求。同时针对 DeepSeek，开启 `response_format={"type": "json_object"}` 强制返回 JSON。

2. **LangGraph 字典覆盖陷阱 (Reducer Issue)**
   - **现象**：使用原生的 `dict` 作为 `StateGraph` 时，节点返回的局部更新覆盖了全量字段（例如导致 `original_goal` 丢失）。
   - **解决**：使用继承自 `TypedDict` 的 `GraphState`，并在没有自定义 Reducer 时，显式地在节点中回传需要的全量状态。

3. **Checkpointer 的 "Unregistered Type" 警告**
   - **现象**：终端黄字警告 `Deserializing unregistered type task_queue.ResearchTask`。
   - **解决**：LangGraph 的 jsonplus 序列化对自定义 Pydantic 类很严格。通过 `logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)` 进行了优雅屏蔽。

4. **缓存污染与相对路径**
   - **现象**：`search_cache.json` 和 `research_checkpoints.sqlite` 直接生成在根目录，导致仓库脏乱。
   - **解决**：使用 `os.path.join(os.path.dirname(__file__), ...)` 确保这些产物和最终生成的报告（`final_research_report.md`）都安静地躺在当前模块下。
