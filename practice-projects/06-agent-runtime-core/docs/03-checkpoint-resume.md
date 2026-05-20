# 阶段 3：Checkpoint / Resume

## 能力定位

Checkpoint / Resume 要验证长任务中断后可以恢复，而不是从头重跑。

Agent Runtime 如果不能恢复，长任务就很难进入真实工程场景。因为模型调用、工具调用、人工介入和网络环境都可能导致中断。

## 当前状态

状态：`completed`

阶段 3 已经新增本地 JSON checkpoint 和顺序 `StepRunner`，可以模拟中断后从 checkpoint 恢复。

## 已实现内容

新增：

```text
runtime_core/observability/checkpoint/
runtime_core/execution/step_runner.py
scripts/run_resume_demo.py
tests/test_checkpoint_resume.py
```

同时更新：

```text
runtime_core/__init__.py
README.md
docs/agent-core-capabilities-validation-plan.md
```

## 最小场景

```text
一个三步任务：
1. collect
2. summarize
3. review

第一次运行在第 2 步后模拟中断。
第二次运行从 checkpoint 恢复，从第 3 步继续。
```

## 设计要点

| 能力 | 说明 |
|------|------|
| checkpoint | 保存 `RuntimeState`、已完成 step、关键 artifact 引用 |
| resume | 读取 checkpoint，跳过已完成 step |
| skipped | 对恢复时跳过的 step 做明确记录 |
| blocked | 遇到不可自动恢复的问题时停下来 |

## 核心对象

| 对象 | 作用 |
|------|------|
| `CheckpointRecord` | 一次 checkpoint 快照，包含 `task_id`、`saved_at` 和 `RuntimeState` |
| `FileCheckpointStore` | 本地 JSON checkpoint store，负责 save / load / clear |
| `StepDefinition` | 一个可执行 step 的定义，包含 step id、名称和 handler |
| `StepRunner` | 顺序执行 step，每个 step 后保存 checkpoint |
| `StepRunReport` | 一次执行报告，记录 completed、skipped、interrupted 和 final status |

## 恢复语义

当前恢复逻辑非常明确：

1. 第一次运行时，`StepRunner` 执行 step。
2. 每个 step 成功后保存 checkpoint。
3. 指定 `stop_after_step_id` 时，模拟中断并把状态标记为 `interrupted`。
4. 第二次运行先读取 checkpoint。
5. 如果某个 step 在 checkpoint 中已经是 `PASSED`，就不重复执行，而是记录 `SKIPPED`。
6. 继续执行未完成 step。
7. 全部 step 完成后，将任务状态标记为 `completed`。

## 需要验证的问题

- 已完成 step 是否不会重复执行。
- checkpoint 是否足够恢复下一步。
- 恢复过程是否可记录、可观察。
- 中断点是否明确，而不是依赖人工猜测。

当前验证结果：

| 问题 | 当前回答 |
|------|----------|
| 已完成 step 是否不会重复执行 | 可以，恢复时 `collect` 和 `summarize` 被标记为 skipped |
| checkpoint 是否足够恢复下一步 | 可以，checkpoint 保存完整 `RuntimeState` |
| 恢复过程是否可观察 | 可以，`StepRunReport` 和 `SKIPPED` step 都记录恢复行为 |
| 中断点是否明确 | 可以，`stop_after_step_id` 模拟明确中断点 |

## 验收标准

- 第一次运行可以在指定 step 后中断。
- 第二次运行能从 checkpoint 恢复。
- trace 或日志能看到恢复和跳过行为。

验证命令：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_resume_demo.py
python3 -m pytest practice-projects/06-agent-runtime-core/tests
```

## Demo 行为

运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_resume_demo.py
```

可以看到：

- 第一次运行完成 `collect` 和 `summarize`。
- 第一次运行在 `summarize` 后模拟中断。
- checkpoint 写入本地临时目录。
- 第二次运行从 checkpoint 恢复。
- `collect` 和 `summarize` 不重复执行，而是记录为 `skipped`。
- 第二次运行只执行 `review`。
- 最终任务状态为 `completed`。

如果需要完整 payload：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_resume_demo.py --format json
```

## 经验教训

- checkpoint 应保存 `RuntimeState`，而不是重新推断“执行到哪里”。
- resume 时必须显式记录 skipped，否则很难复盘哪些 step 被跳过、哪些 step 重新执行。
- 每个 step 成功后立即保存 checkpoint，比只在任务结束时保存更适合长任务恢复。
- 当前本地 JSON checkpoint 只适合验证恢复语义，不适合并发或分布式运行。

## 当前边界

本阶段不做：

- 分布式 checkpoint。
- 数据库事务。
- 多 worker 并发恢复。
- 复杂 DAG 调度。

先验证本地文件级 checkpoint 是否足够表达恢复语义。

## 后续增强清单

| 能力 | 说明 | 建议时机 |
|------|------|----------|
| checkpoint schema version | 给 checkpoint 增加版本，支持后续兼容升级 | RuntimeState 结构稳定后 |
| checkpoint store 抽象 | 将本地 JSON 替换为 SQLite 或数据库实现 | 需要和 memory / trace store 统一存储时 |
| running step 恢复策略 | 处理中断时处于 RUNNING 的 step，是重试、失败还是 blocked | 引入真实工具调用后 |
| blocked 状态 | 对缺少权限、缺少人工输入、无法自动恢复的情况显式停止 | tool policy 阶段 |
| retry 策略 | 对可重试 step 做有限重试和失败记录 | 接入不稳定工具或 LLM 后 |
| DAG 调度 | 支持非线性 step 依赖 | 最小顺序 runner 不够用时 |
