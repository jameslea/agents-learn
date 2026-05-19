# 阶段 3：Checkpoint / Resume

## 能力定位

Checkpoint / Resume 要验证长任务中断后可以恢复，而不是从头重跑。

Agent Runtime 如果不能恢复，长任务就很难进入真实工程场景。因为模型调用、工具调用、人工介入和网络环境都可能导致中断。

## 当前状态

状态：`pending`

当前只有内存态 `RuntimeState`，还没有 checkpoint 文件、resume 策略和 step runner。

## 计划实现

预计新增：

```text
runtime_core/checkpoint.py
runtime_core/step_runner.py
scripts/run_resume_demo.py
tests/test_checkpoint_resume.py
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

## 需要验证的问题

- 已完成 step 是否不会重复执行。
- checkpoint 是否足够恢复下一步。
- 恢复过程是否可记录、可观察。
- 中断点是否明确，而不是依赖人工猜测。

## 验收标准

- 第一次运行可以在指定 step 后中断。
- 第二次运行能从 checkpoint 恢复。
- trace 或日志能看到恢复和跳过行为。

## 当前边界

本阶段不做：

- 分布式 checkpoint。
- 数据库事务。
- 多 worker 并发恢复。
- 复杂 DAG 调度。

先验证本地文件级 checkpoint 是否足够表达恢复语义。
