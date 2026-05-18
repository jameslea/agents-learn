# Agent Runtime & Governance Lab MVP 收束记录

> 更新时间：2026-05-18
>
> 本文用于冻结项目 E 当前阶段的边界和结论。它不是新的开发计划，而是对当前 MVP 状态的验收记录，方便后续继续推进时不重新争论方向。

## 1. 阶段结论

当前项目 E 已完成一次可运行的 Agent Runtime MVP。

它的价值不在于做了一个新的 Agent demo，而在于把多个 Agent 项目反复需要的公共运行能力抽离出来：

```text
TaskContract
  -> AgentAdapter
  -> RuntimeState / StepExecution
  -> GovernedToolRunner
  -> Artifact / ArtifactStore
  -> Trace / Replay
  -> EvaluationResult
  -> Human Review
  -> RunLock / run_id
```

因此，当前阶段可以收束为：

```text
Agent Runtime = 承载不同 Agent 项目执行的公共运行环境
Evaluation / Observability = Runtime 的配套验证能力
```

这修正了早期偏向“跨项目评测”的方向，把项目重新拉回 Runtime Core。

## 2. 已完成能力

| 能力 | 当前状态 |
|------|----------|
| 任务契约 | `TaskContract` 定义目标、输入、成功标准、风险等级、允许工具和预算 |
| 项目接入 | `AgentAdapter` 让不同 Agent 项目接入统一 Runtime 生命周期 |
| 步骤状态 | `RuntimeState / StepExecution` 记录步骤开始、完成、失败和跳过 |
| 状态持久化 | `RuntimeCheckpointStore` 保存 checkpoint，支持失败复盘和最小 resume |
| 产物管理 | `Artifact` 表达结构化产物，`LocalArtifactStore` 保存大段中间产物 |
| 工具治理 | `ToolPolicy / GovernedToolRunner` 管理工具权限、路径边界、风险和审批 |
| Trace 回放 | JSONL trace 记录 task、step、tool、artifact、evaluation 和终态，支持 replay |
| 人工介入 | 高风险动作可进入 `needs_human`，批准后才继续执行 |
| LLM Reviewer | 报告治理场景支持可选 LLM review，但不把模型判断作为最终裁决 |
| 运行锁 | `RuntimeRunLock` 防止同一 adapter 并发写入同一组运行产物，并可清理记录了失效 pid 的 stale lock |
| 运行隔离 | `run_id` 支持 trace、checkpoint、artifact、lock 和场景输出按运行实例隔离 |
| 运行索引 | `RuntimeRunManifest` 记录一次运行的 trace、checkpoint、artifact root、状态和摘要 |
| LLM 最小指标 | LLM reviewer 记录 provider、model、latency、status 和 failure reason 字段；调用失败不覆盖确定性评估结果 |

## 3. 可运行样本

当前有三类样本，各自定位不同：

| 样本 | 定位 | 说明 |
|------|------|------|
| 报告治理场景 | Runtime 原生场景 | 用确定性质量规则、工具治理、LLM reviewer 和人工审批验证 Runtime 能力 |
| B-runtime-lite | 真实 runtime execution | 从 topic 开始生成大纲、草稿、审阅、改进计划、修订和最终报告 |
| D-lite adapter | 旧项目 runtime wrapper | 保留自愈实验内部逻辑，由 Runtime 包住生命周期、artifact 和 evaluation |
| A/B/C observability adapter | 观测样本 | 读取已有产物做 readiness / quality / structure 检查，不称为真实 runtime execution |

这个区分很重要：读取已有产物只能证明观测和验证能力，不能证明 Runtime 承载了原始 Agent 执行过程。

## 4. 当前验收命令

运行测试：

```bash
python3 -m pytest practice-projects/05-agent-runtime-governance/tests
```

运行 B-runtime-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py
```

运行具名隔离实例：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py --run-id experiment-001
```

从具名 checkpoint 恢复：

```bash
python3 practice-projects/05-agent-runtime-governance/run_content_runtime.py --run-id experiment-001 --resume
```

回放最新 trace：

```bash
python3 practice-projects/05-agent-runtime-governance/run_trace_replay.py
```

运行报告治理场景：

```bash
python3 practice-projects/05-agent-runtime-governance/run_report_governance.py
```

运行 D-lite：

```bash
python3 practice-projects/05-agent-runtime-governance/run_d_lite_runtime.py
```

观测 A/B/C 已有产物：

```bash
python3 practice-projects/05-agent-runtime-governance/run_project_observability.py
```

## 5. 明确边界

当前已经足够作为学习和方法论验证项目，但还不是生产级框架。

当前不包含：

- 通用 step graph / DAG 调度。
- 服务化 API、队列、worker 池或 UI。
- 数据库级状态存储。
- 完整 RBAC、凭证管理和审计系统。
- 云平台、Kubernetes、CI/CD 或真实运维环境接入。
- 多模态实时系统。
- 外部可视化观测平台接入。

这些能力可以作为后续工程化方向，但不应反向要求当前 MVP 承担产品级复杂度。

## 6. 已知风险

| 风险 | 当前处理 |
|------|----------|
| stale lock | 新格式 lock 会记录 pid，Runtime 可清理 pid 已失效的 stale lock；旧格式或无法判断 pid 的 lock 仍需人工检查 |
| step 调度简单 | 当前是顺序步骤，尚无通用 DAG、条件分支和重试调度 |
| policy 配置内嵌 | `ToolPolicy` 主要由代码构造，尚未外部化为策略文件 |
| LLM 统计不足 | 已有 provider、model、latency、status、failure reason；token 和 cost 仍未形成统一指标 |
| adapter runtime 样本偏少 | B-runtime-lite 和 D-lite 已可运行，但 A/B/C 仍主要是 observability |
| trace payload 控制 | 已用 artifact ref 减少大 payload，但 tool input 摘要仍可继续压缩 |

## 7. 下一阶段选择

当前 E-Mini Hardening 收尾已完成，不建议立即进入多模态。更合理的后续分支有两个：

| 方向 | 价值 | 适合条件 |
|------|------|----------|
| Runtime 工程化增强 | 稳定 Runtime Core，补策略文件、step retry、更多 LLM metrics | 希望把 Runtime 作为长期公共底座 |
| 第二个真实 Agent 场景 | 验证 Runtime 是否能适配内容生产以外的 Agent 执行链路 | 希望尽快暴露 adapter 抽象的不足 |

建议优先级：

1. 将 `ToolPolicy` 从代码配置推进到可读策略文件。
2. 为 step 增加最小 retry / failure policy。
3. 为 LLM 调用补 token、cost 等更完整指标。
4. 选择一个比 B-runtime-lite 更接近真实任务的第二个 runtime execution 场景。

## 8. 收束判断

本阶段可以关闭为：

```text
项目 E MVP：完成
E-Mini Hardening：完成
主线方向：Agent Runtime Core
当前产出：可运行代码 + 测试 + trace/replay + 文档化方法论
下一步：暂停扩展，或选择策略文件 / step retry / 第二真实场景中的一个小任务
```

后续继续开发时，应以这份收束记录作为起点，避免重新把项目退回“评测脚本”或“堆更多 Agent demo”的方向。
