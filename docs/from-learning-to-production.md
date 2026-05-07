# 从学习到实战：真实 Agent 项目落地建议

> 本文基于 `agents-learn` 仓库全部 15 阶段 + 4 章架构深潜的沉淀，给出从代码实践到生产级 Agent 项目的完整行动框架。

---

## 目录

- [一、先选场景，后选技术](#一先选场景后选技术)
- [二、从 Demo 到生产的五道坎](#二从-demo-到生产的五道坎)
  - [坎 1：状态不是字典，是生存问题](#坎-1状态不是字典是生存问题)
  - [坎 2：同步调用是定时炸弹](#坎-2同步调用是定时炸弹)
  - [坎 3：评估不是事后，是 CI 的一部分](#坎-3评估不是事后是-ci-的一部分)
  - [坎 4：安全不是护栏，是最小权限](#坎-4安全不是护栏是最小权限)
  - [坎 5：上下文管理不是修剪，是架构设计](#坎-5上下文管理不是修剪是架构设计)
- [三、分阶段推进计划](#三分阶段推进计划)
  - [Phase 0：场景验证（1-2 周）](#phase-0场景验证1-2-周)
  - [Phase 1：最小骨架（2-3 周）](#phase-1最小骨架2-3-周)
  - [Phase 2：评估先行（1 周）](#phase-2评估先行1-周)
  - [Phase 3：纵向加固（持续）](#phase-3纵向加固持续)
  - [Phase 4：按需扩展（按业务需求）](#phase-4按需扩展按业务需求)
- [四、可以直接复用的资产](#四可以直接复用的资产)

---

## 一、先选场景，后选技术

这个仓库的核心结论之一：**没有银弹，按场景选模式**。从 `AGENTS_KNOWLEDGE_MAP.md` 中提炼的选型矩阵：

| 你的业务特征 | 推荐架构组合 |
|---|---|
| 知识库问答，准确率要求极高 | LlamaIndex + HyDE+Rerank + Self-RAG 闭环 |
| 多角色协作（如内容生产、报告生成） | LangGraph(总控) + CrewAI/SOP 风格子任务 |
| 开放式调研、自动化分析 | BabyAGI 风格任务循环 + 人类检查点 |
| 需要反复调试的代码/运维任务 | AutoGen 对话式自愈（代码 Agent 左右互搏） |
| 快速交付给业务方 | Dify/Coze 原型 → 验证需求 → 必要时迁移到代码框架 |

**第一建议**：不要在真实项目里押注单一框架。仓库反复强调的架构模式是：

```
LangGraph → 主流程编排（骨架）
专用 Agent → 动态子任务执行（大脑）
LlamaIndex → 数据检索层（知识）
评估 + 观测 → 上线治理（眼睛）
```

---

## 二、从 Demo 到生产的五道坎

这是仓库 `docs/NEXT_STEPS.md` 和 architecture-deep-dives 反复点出的差距：

### 坎 1：状态不是字典，是生存问题

仓库阶段 05 用 Pydantic + Enum 消灭魔法字符串只是起点。生产环境里，你需要回答：
- Agent 运行到第 4 步宕机了，重启后是重做第 4 步还是跳过？
- 如果第 3 步已经调了一次支付接口，重放怎么办？（architecture-deep-dives Chapter 3 的副作用重放陷阱）
- 恢复时外部状态已经变了，Agent 怎么感知？

**落地建议**：从 `SqliteSaver` 开始（仓库 architecture-deep-dives 实验 1.4 的模式），但预留迁移到 PostgreSQL Checkpointer 的接口。

### 坎 2：同步调用是定时炸弹

Agent 不能跑在 HTTP 请求的同步线程里。一个复杂任务可能跑 5 分钟，用户早超时了。architecture-deep-dives Chapter 3 的建议路径：

```
单机 asyncio → SQLite Checkpoint → 消息队列 + LangGraph → Temporal
```

**落地建议**：第一天就用 `asyncio` + 后台任务队列（Celery/Redis Streams），不要让 Agent 逻辑直接绑在 Web 框架的 request handler 里。

### 坎 3：评估不是事后，是 CI 的一部分

仓库阶段 15 和 architecture-deep-dives Chapter 4 的核心信息：**没有自动化评估的上线等于闭眼开车**。至少需要三条线：
- **忠实度**：Agent 的回答是否基于检索到的文档（而不是幻觉）
- **工具调用成功率**：Agent 调用工具的准确率
- **端到端任务完成率**：给定 20 个真实用户场景，一次性完成的百分比

**落地建议**：先手工标注 20-50 条 Golden Dataset，再用 RAGAS 或 LLM-as-a-Judge 自动化。这是仓库 `docs/NEXT_STEPS.md` 阶段二的建议。

### 坎 4：安全不是护栏，是最小权限

architecture-deep-dives Chapter 4 的核心原则：**最小权限比任何 Guardrails 都重要**。一个没有 `send_email` 工具的 Agent，即使被 Prompt Injection 攻击，也无法发邮件。

**落地建议**：
- 工具按风险分级（只读 / 写内部 / 写外部）
- 高风险工具必须人类确认（Human-in-the-loop）
- 代码执行走沙箱/Docker，不走宿主机

### 坎 5：上下文管理不是修剪，是架构设计

仓库 `docs/plan2.md` 提出的四维观察框架中，"上下文治理与精简"是独立维度。随着任务链增长，Agent 的注意力会非线性衰减。

**落地建议**：
- 长任务中间插入"摘要节点"，把历史压缩后再传给下一节点
- 只给 Agent 当前任务需要的信息，而不是全量上下文

---

## 三、分阶段推进计划

参考仓库自身从 01 到 15 的递进逻辑，建议真实项目这样推进：

### Phase 0：场景验证（1-2 周）
- 手工跑通 3-5 个端到端场景，不写任何框架代码
- 用 LLM 直接对话，验证可行性
- 产出：场景清单 + 失败模式列表

### Phase 1：最小骨架（2-3 周）
- LangGraph 定义主流程（3-5 个节点即可）
- 一个工具（搜索或知识库检索）
- SQLite Checkpointer
- 不做多 Agent，不搞花活

### Phase 2：评估先行（1 周）
- 标注 Golden Dataset（20 条）
- 搭建 RAGAS 评估脚本
- **在加任何新功能之前，先锁定当前质量基线**

### Phase 3：纵向加固（持续）
- 消息队列解耦
- 错误重试 + 降级 + 超时
- 敏感操作人类确认
- Langfuse/类似工具全链路追踪

### Phase 4：按需扩展（按业务需求）
- 需要更好的检索 → 引入 HyDE + Rerank
- 需要多角色协作 → 引入 Supervisor/子 Agent
- 需要知识积累 → 引入技能库

---

## 四、可以直接复用的资产

这个仓库里可以直接当"零件"拆出去用的：

| 你想做的事 | 直接看这里 |
|---|---|
| LangGraph 生产级状态机模板 | `05-final-project/` 的 Pydantic + Enum 范式 |
| 多 Agent 调度器 | `04-multi-agent/` 的 Supervisor 模式 |
| 代码执行安全方案 | `09-execution-depth/` 的 AST vs Subprocess 对比 |
| RAG 选哪个检索方案 | architecture-deep-dives Chapter 2 的 6 模式决策矩阵 |
| 分布式 Agent 架构设计 | architecture-deep-dives Chapter 3 的消息队列选型 + Checkpoint 断点续传 |
| 上线前的安全检查清单 | `15-production-agent-engineering/` 的 guardrails_demo.py |
| AutoGen 自愈模式 | `08-autogen-intro/` + `09-execution-depth/self_heal_autogen.py` |
| 踩坑速查 | `docs/TROUBLESHOOTING.md` |

---

**一句话总结**：选一个小场景，LangGraph 搭骨架，评估先于功能，异步从第一天就做，最小权限管住工具——这是这个仓库通篇在重复的路径。
