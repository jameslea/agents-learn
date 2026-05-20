# 阶段 7：code_review_mini 场景试验

## 能力定位

`code_review_mini` 用一个具体代码审查场景验证 Runtime Core 是否能被非 research 类 Agent 复用。

目标不是开发完整代码审查产品，而是观察：

- 场景代码如何复用 Runtime Core public API。
- 真实 LLM 输出如何通过 schema artifact 进入后续流程。
- Runtime Core 当前接口有哪些使用摩擦。

## 当前状态

状态：`completed`

该场景默认使用离线 deterministic reviewer，便于测试和稳定复盘；也支持通过 `--llm` 使用仓库统一 LLM provider。

## 实现文件

相对代码根目录：`practice-projects/06-agent-runtime-core/`

```text
scenarios/code_review_mini/
  schemas.py
  llm_reviewer.py
  scenario.py
  sample_target.py
scripts/run_code_review_mini.py
tests/test_code_review_mini.py
```

## 场景流程

```text
collect_code_context -> CodeSnapshot
llm_or_rule_review  -> ReviewReport
propose_patch       -> PatchSuggestion
```

其中：

- `CodeSnapshot` 保存被审查代码快照。
- `ReviewReport` 保存结构化审查发现。
- `PatchSuggestion` 只保存补丁建议，不直接修改文件。

## Runtime Core 复用情况

| Runtime 能力 | 场景用法 |
|--------------|----------|
| `TaskContract` | 定义代码审查任务目标、输入和成功标准 |
| `MinimalRuntime` | 串联 state、context、artifact、checkpoint 和 trace |
| `ContextBuilder` | 为读取代码、审查代码、生成 patch suggestion 构造当前 step 工作视图 |
| `MemoryRecord` | 提供项目级代码审查偏好，例如高风险动作需要人工确认 |
| `ArtifactRecord` | 保存 `CodeSnapshot`、`ReviewReport`、`PatchSuggestion` |
| `TraceRecorder` | 记录文件读取、reviewer 调用、patch policy 检查和 artifact 流转 |
| `ToolPolicyChecker` | 区分只读文件读取、只读 patch suggestion 和需要审批的 patch writer |
| `Blocked` | 当尝试使用需要审批的 patch writer 时进入 blocked |

## 运行方式

离线运行：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset
```

使用真实 LLM：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --llm
```

指定 LLM provider / model：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --llm --provider minimax --model MiniMax-M2.7
```

观察日志默认带时间戳，输出包括：

- `reviewer_provider`
- `reviewer_model`
- `reviewer_status`
- `reviewer_latency_ms`
- `reviewer_prompt_chars`
- `reviewer_response_chars`
- `reviewer_failure_reason`

模拟中断恢复：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --stop-after llm_or_rule_review
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py
```

模拟工具审批阻塞：

```bash
python3 practice-projects/06-agent-runtime-core/scripts/run_code_review_mini.py --reset --force-blocked
```

## 经验记录

本场景暴露出的第一批 Runtime Core 使用摩擦：

- LLM reviewer 仍需要场景侧包装，Runtime Core 当前没有通用 LLM step adapter。这个暂时合理，因为不同场景的 prompt、schema 和失败处理差异很大。
- 真实 LLM 输出必须由场景 schema 做强校验，不能让 Runtime Core 直接理解业务 JSON。
- `ToolPolicyChecker` 可以表达审批要求，但“blocked 还是只输出建议”的决策仍属于场景。
- `MinimalRuntime` 对线性 step 场景够用，但如果代码审查后续加入多文件并行检查，可能会暴露 DAG 或批处理需求。

## 当前边界

本阶段不做：

- 自动修改代码文件。
- 自动执行测试。
- 多文件递归审查。
- LLM 失败自动重试。
- 向量检索或持久化 memory store。

这些能力应等更多场景验证后再决定是否进入 Runtime Core。
