# 实战项目矩阵：五场景全覆盖，每坑必填

> 基于 `docs/from-learning-to-production.md` 的五种业务场景，拆解为五个独立实践项目。
> 每个项目有明确的**目标、技术栈、核心坑位清单、验收标准**。
> 五个项目全部做完，覆盖本项目识别的全部生产级问题。

---

## 目录

- [项目全景图](#项目全景图)
- [环境前置条件](#环境前置条件)
- [项目 A：企业知识库问答系统](#项目-a企业知识库问答系统)
- [项目 B：内容创作团队](#项目-b内容创作团队)
- [项目 C：自主调研助手](#项目-c自主调研助手)
- [项目 D：自愈运维 Agent](#项目-d自愈运维-agent)
- [项目 E：评估与安全防线（横向基础设施）](#项目-e评估与安全防线横向基础设施)
- [推进顺序](#推进顺序)
- [每个项目的 README 模板](#每个项目的-readme-模板)
- [预估总工作量](#预估总工作量)

---

## 项目全景图

```
项目 A：知识库问答 —— 数据中心型
项目 B：内容创作团队 —— 多角色协作型
项目 C：自主调研助手 —— 任务循环型
项目 D：自愈运维 Agent —— 对话自愈型
项目 E：评估与安全防线 —— 治理底座型（横向穿透所有项目）
```

其中项目 E 不独立存在，而是作为 A-D 的评估/观测/安全基础设施，每个项目都接一套。

---

## 环境前置条件

所有项目共享以下基础依赖，请在启动第一个项目前确认就绪：

| 依赖 | 最低要求 | 用于 | 备注 |
|------|---------|------|------|
| Python | 3.10+ | 所有项目 | 推荐 3.11+，LangGraph / AutoGen 0.4 需要 |
| LLM API | 至少一个可用 | 所有项目 | DeepSeek / OpenAI / 本地 Ollama 均可；项目 A 的 HyDE 和 Self-RAG 需要较强模型 |
| Docker Desktop | 最新稳定版 | 项目 D | 自愈运维的沙箱执行依赖 `DockerCommandLineCodeExecutor` |
| 向量数据库 | ChromaDB 或 FAISS | 项目 A、C | `pip install chromadb` 即可，无需额外服务 |
| GPU / Apple MPS | 可选但推荐 | 项目 A | Cross-Encoder Rerank 在 CPU 上较慢；Mac M 系列可自动使用 MPS 加速 |
| Langfuse | Cloud 免费版或自托管 | 项目 E | 自托管需 Docker Compose；Cloud 版注册即用，推荐初期使用 Cloud 版 |

> **提示**：如果只想快速验证一个项目，最精简的配置是：Python 3.11 + DeepSeek API + ChromaDB。Docker 和 Langfuse 可以在进入项目 D 和项目 E 时再准备。

---

## 项目 A：企业知识库问答系统

**场景**：内部文档（制度、技术方案、会议纪要）的精准问答。不允许幻觉。

**技术栈**：
- LlamaIndex（数据接入、索引、查询引擎）
- HyDE 查询改写 + Cross-Encoder Rerank
- LangGraph Self-RAG 闭环（检索 → 评估 → 改写 → 兜底搜索 → 生成）
- ChromaDB / FAISS 向量存储
- Pydantic 状态管理

**核心坑位清单**：

| 编号 | 坑 | 来源 |
|------|-----|------|
| A1 | 语义混淆：一词多义导致检索漂移 | architecture-deep-dives Ch2 |
| A2 | 多跳推理：跨文档逻辑链断裂 | architecture-deep-dives Ch2 |
| A3 | 文档分块策略不当，关键信息被截断 | 数据工程实战 |
| A4 | 检索结果质量无评估，幻觉静默传播 | Self-RAG 闭环 |
| A5 | PDF 表格/图片解析失败 | architecture-deep-dives Ch2 ETL |
| A6 | 知识库更新后旧索引未失效 | 生产运维 |
| A7 | HyDE 改写引入噪声（改写偏离原意） | architecture-deep-dives Ch2 |

**目录结构**：
```
practice-projects/01-knowledge-base-qa/
  data/                    # 测试文档集（含混淆文本、跨文档推理素材）
  ingestion.py             # 文档解析 + 分块 + 索引
  query_engine.py          # 基础检索
  hyde_rewriter.py         # HyDE 查询改写
  reranker.py              # Cross-Encoder 重排序
  self_rag_graph.py        # LangGraph Self-RAG 闭环
  evaluate.py              # 检索命中率 + 忠实度评估
  README.md                # 项目说明 + 踩坑记录
```

**验收标准**：
- 在构造的语义混淆测试集上达到 >90% 命中率
- Self-RAG 闭环：检索质量低时自动改写查询，改写后仍低则走网络搜索兜底
- 每个坑位有对应测试用例和踩坑记录

---

## 项目 B：内容创作团队

**场景**：给定一个主题，多角色协作生成结构化的深度报告/文章。
角色链：产品经理（需求拆解）→ 研究员（资料搜集）→ 分析师（数据解读）→ 撰稿人（生成报告）→ 评审员（质量审核）。

**技术栈**：
- LangGraph Supervisor 模式（总控调度）
- CrewAI 风格角色定义（Role / Goal / Backstory）
- SOP 结构化中间产物（PRD、研究摘要、数据报告、初稿、评审意见）
- Pydantic 强类型产物传递

**核心坑位清单**：

| 编号 | 坑 | 来源 |
|------|-----|------|
| B1 | 角色边界模糊，一个 Agent 越权干另一个的活 | 多 Agent 协作 |
| B2 | 任务交接时信息丢失或格式不一致 | 结构化产物 |
| B3 | 评审 Agent 永远不满意，陷入死循环 | 终止条件 |
| B4 | 某个角色输出质量差，下游全崩 | 中间审核 |
| B5 | 对话上下文膨胀，后期 Agent 注意力衰减 | 上下文治理 |
| B6 | 产物版本混乱，不知道哪版是最终 | 状态管理 |
| B7 | 人类在关键节点无法介入 | Human-in-the-loop |

**目录结构**：
```
practice-projects/02-content-creation-team/
  crew/
    product_manager.py     # PM Agent
    researcher.py          # 研究员 Agent
    analyst.py             # 分析师 Agent
    writer.py              # 撰稿人 Agent
    reviewer.py            # 评审员 Agent
  supervisor_graph.py      # LangGraph Supervisor 总控
  sop_artifacts.py         # 中间产物 Pydantic 模型
  human_review_node.py     # 人类确认节点
  evaluate.py              # 端到端任务完成率评估
  README.md
```

**验收标准**：
- 4 个以上角色协作完成一篇 2000+ 字深度报告
- 每个角色的中间产物结构化存储（JSON/Pydantic）
- 评审循环最多 3 轮，超限强制终止并标记
- 至少一个关键节点成功插入人类确认

---

## 项目 C：自主调研助手

**场景**：用户给一个长期目标（如"调研 2026 年 AI Agent 编程工具的竞争格局"），Agent 自己拆解任务、逐项执行、反思结果、更新计划，最终输出调研报告。

**技术栈**：
- BabyAGI 风格任务队列（优先级、依赖、状态）
- LangGraph 任务循环图
- Tavily / DuckDuckGo 搜索
- 摘要节点（上下文压缩）
- SQLite Checkpointer（断点续传）

**核心坑位清单**：

| 编号 | 坑 | 来源 |
|------|-----|------|
| C1 | 目标漂移：Agent 跑着跑着忘了最初要干什么 | 任务循环 |
| C2 | 无限循环：一直创建新任务，永不停机 | 停止条件 |
| C3 | 成本失控：一个调研跑了 50 次 LLM 调用 | 成本控制 |
| C4 | 任务优先级不合理，重要的事排最后 | 优先级算法 |
| C5 | 执行中途宕机，重启后状态丢失或重复执行 | Checkpoint |
| C6 | 上下文超出窗口，前期搜索结果被遗忘 | 上下文治理 |
| C7 | 搜索结果质量差但 Agent 不会质疑 | 反思机制 |

**目录结构**：
```
practice-projects/03-autonomous-research/
  task_queue.py            # 任务队列（优先级/依赖/状态机）
  task_generator.py        # 从目标生成任务
  task_executor.py         # 执行单个任务（搜索+总结）
  reflector.py             # 反思节点：结果评估 + 计划更新
  research_graph.py        # LangGraph 任务循环图
  checkpoint_test.py       # 断点续传测试（模拟宕机）
  cost_tracker.py          # Token 消耗追踪 + 预算控制
  README.md
```

**验收标准**：
- 从一个模糊目标出发，自动生成并执行 8+ 个任务
- 总步数 >15 时强制停止并输出已完成部分
- 模拟宕机后能从 Checkpoint 恢复，不重复执行已完成任务
- 单次调研 Token 消耗 < 50000（可配置上限）

---

## 项目 D：自愈运维 Agent

**场景**：给 Agent 一个代码任务（如"写一个爬虫抓取某网站数据"），Agent 写代码 → 在 Docker 沙箱执行 → 遇到报错 → 自己分析报错 → 修改代码 → 重新执行，直到成功。

**技术栈**：
- AutoGen 0.4+（`autogen-agentchat` / `autogen-core` / `autogen-ext`，与仓库 `08-autogen-intro/` 一致）
- 对话式多 Agent（Coder + Executor + Reviewer），基于 `RoundRobinGroupChat` 或 `SelectorGroupChat`
- Docker 沙箱执行（`DockerCommandLineCodeExecutor`，物理隔离）
- AST 安全检查（smolagents 风格）作为第二道防线
- 最大重试次数 + 超时熔断

**核心坑位清单**：

| 编号 | 坑 | 来源 |
|------|-----|------|
| D1 | 代码执行安全：Agent 可能生成危险代码 | 执行安全 |
| D2 | 报错信息太长，Agent 抓不住重点 | 错误压缩 |
| D3 | 修复循环：改了 A 坏了 B，无限反复 | 终止条件 |
| D4 | Docker 环境与宿主机不一致，能跑但结果不对 | 环境一致性 |
| D5 | 依赖安装失败，Agent 不会排查 | 错误分类 |
| D6 | 执行超时，Agent 不感知 | 超时处理 |
| D7 | 自愈后代码质量下降（打补丁式修复） | 代码审查 |

**目录结构**：
```
practice-projects/04-self-healing-ops/
  agents/
    coder.py               # 编码 Agent
    executor.py            # 执行 Agent（Docker 沙箱）
    reviewer.py            # 审查 Agent
  sandbox/
    Dockerfile             # 沙箱镜像
    sandbox_manager.py     # 容器生命周期管理
  ast_checker.py           # AST 安全检查
  self_heal_graph.py       # AutoGen 对话流 + LangGraph 编排
  error_classifier.py      # 报错分类 + 压缩
  challenge_tasks/         # 故意埋坑的测试任务
    task1_broken_import.py
    task2_infinite_loop.py
    task3_permission_error.py
  README.md
```

**验收标准**：
- 给定 3 个故意有 bug 的任务（缺依赖/死循环/权限错误），Agent 自主修复成功率 > 66%
- 危险代码（如 `os.system("rm -rf /")`）被 AST 检查器拦截
- 最大重试 5 次，超限终止
- Docker 容器执行后自动销毁，不留残留

---

## 项目 E：评估与安全防线（横向基础设施）

**不是独立项目**——作为 A-D 每个项目的 `evaluate.py` 和 `security.py` 存在，同时有一个共享的评估框架。

**技术栈**：
- RAGAS（忠实度、相关性评估）
- LLM-as-a-Judge（工具调用成功率、任务完成率）
- Langfuse（全链路 Trace 追踪）
- Guardrails（输入/输出护栏）
- Prompt Injection 防御

**核心坑位清单**：

| 编号 | 坑 | 来源 |
|------|-----|------|
| E1 | 评估指标设计不合理，高分但实际不好用 | 评估体系 |
| E2 | LLM-as-a-Judge 自己也有偏见，评测结果不可信 | 评估方法论 |
| E3 | Trace 太多太乱，找不到瓶颈 | 可观测性 |
| E4 | Prompt Injection：用户输入伪装成系统指令 | 安全 |
| E5 | 工具权限过大，攻击面宽 | 最小权限 |
| E6 | 评估集过时，测不出新问题 | 评估维护 |
| E7 | 护栏误拦正常请求，用户体验差 | 护栏调优 |

**目录结构**：
```
practice-projects/00-evaluation-infra/
  eval_framework/
    ragas_runner.py         # RAGAS 评估执行器
    llm_judge.py            # LLM-as-a-Judge
    metrics.py              # 指标定义
    golden_dataset.py       # 黄金测试集管理
  observability/
    langfuse_tracer.py      # Trace 集成
    cost_dashboard.py       # 成本监控
  security/
    input_guard.py          # 输入护栏
    output_guard.py         # 输出护栏
    injection_test.py       # Prompt Injection 攻击用例
    tool_permission.py      # 工具权限分级
  README.md
```

**验收标准**：
- 每个项目 A-D 都接入了评估流水线，跑一次出三个数字（忠实度/工具成功率/任务完成率）
- Langfuse Trace 能回溯任意一次失败调用的完整链路
- Prompt Injection 攻击用例库至少 10 条，护栏拦截率 > 90%
- 工具按只读/写内部/写外部三级分级，高风险操作强制确认

---

## 推进顺序

```
第一轮：项目 A（知识库问答）
  → 熟悉 LlamaIndex + Self-RAG，填坑 A1-A7
  → 同时搭建项目 E 的评估基础设施

第二轮：项目 C（自主调研）
  → 理解任务循环和 Checkpoint，填坑 C1-C7
  → 项目 E 加入 Langfuse 观测

第三轮：项目 B（内容创作团队）
  → 掌握多 Agent 协作和 SOP，填坑 B1-B7
  → 项目 E 加入安全护栏

第四轮：项目 D（自愈运维）
  → 攻克代码执行安全和自愈循环，填坑 D1-D7
  → 项目 E 完善注入防御

全程：项目 E 随 A→D 逐步生长
```

**为什么不按 A→B→C→D 顺序**：
- A（知识库）和 C（任务循环）的耦合最低，可独立启动
- C 涉及的 Checkpoint 是分布式基础，早学早受益
- B（多 Agent）复杂度最高，放在中间趁手热
- D（自愈）需要 Docker + AST + AutoGen，环境搭好后放最后

---

## 每个项目的 README 模板

每个实践项目建议遵循统一的记录格式：

```markdown
# 项目 X：[名称]

## 场景描述
[一句话说清做什么]

## 技术栈
[列出核心依赖]

## 坑位地图
| 编号 | 坑 | 现象 | 根因 | 方案 | 状态 |
|------|-----|------|------|------|------|
| X1  | ... | ...  | ...  | ...  | ✅/🔄/⏳ |

## 运行方式
```bash
pip install -r requirements.txt
python main.py
```

## 踩坑记录
[自由文本，记录过程中任何计划外的发现]
```

---

## 预估总工作量

| 项目 | 预估时间 | 重点 |
|------|---------|------|
| A 知识库问答 | 2-3 周 | 数据工程 + 检索质量 |
| C 自主调研 | 2-3 周 | 任务循环 + Checkpoint |
| B 内容创作团队 | 2-3 周 | 多 Agent 协作 + SOP |
| D 自愈运维 | 2-3 周 | 沙箱安全 + 自愈循环 |
| E 评估基础设施 | 随 A-D 生长 | 每个项目 +2 天 |
| **合计** | **10-14 周** | 全部坑位覆盖 |

---

**核心思路**：不求每个项目做到生产级完善，而是每个项目**刻意暴露并解决一组特定的坑**。五个项目做完，生产环境的主要陷阱就都有第一手经验了。
