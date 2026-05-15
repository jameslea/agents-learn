# 项目 D-lite：代码执行安全与自愈最小实验

## 场景描述

给 Agent 一个小型 Python 脚本或故意损坏的 challenge task，让它在受限工作目录中执行、识别错误、生成最小修复，再用客观验证信号判断是否修复成功。

本项目不做通用自愈运维平台，不接 Kubernetes、SSH、CI 或云厂商 API。目标是学习代码执行型 Agent 的最小自愈闭环。

## 当前能力

- AST 安全检查：拦截 `os.system`、`subprocess`、危险删除、网络库等高风险行为。
- 临时目录执行：challenge task 会先复制到 `workspaces/`，不修改原始文件。
- 超时熔断：死循环任务会被 timeout 捕获。
- 错误分类：支持 import、syntax、timeout、assertion/runtime、安全拦截等分类。
- 规则型修复 Agent：先用确定性规则验证机制，不依赖 LLM。
- 客观验证：以退出码、断言、超时和安全检查作为通过依据。
- 轻量 trace：每轮运行写入 `traces/*.jsonl`。

## 运行方式

```bash
cd practice-projects/04-self-healing-ops
python3 evaluate.py
```

运行单个任务：

```bash
python3 self_heal_loop.py task3_infinite_loop.py
```

## 主要代码文件

| 文件 | 作用 | 阅读重点 |
|------|------|----------|
| `self_heal_loop.py` | 单任务自愈主循环入口 | `run_self_heal()` 串起复制、验证、分类、修复、再验证和 trace |
| `state.py` | 自愈闭环的数据结构定义 | `RunResult`、`ErrorSummary`、`VerificationResult`、`SelfHealState` 是各模块交接契约 |
| `verification.py` | 客观验证入口 | 先做 AST 安全检查，再运行脚本；只有退出码为 0 且未超时才算通过 |
| `executor.py` | 工作目录准备和脚本执行 | challenge task 会复制到 `workspaces/`，原始文件不被修改 |
| `ast_checker.py` | 静态安全检查 | 拦截网络、shell、删除文件、动态执行等高风险 import/call |
| `error_classifier.py` | 错误分类和证据压缩 | 把 timeout、syntax、import、assertion、runtime、安全拦截转成 `ErrorSummary` |
| `agent.py` | 当前规则型修复 Agent | 暂不调用 LLM，用确定性规则验证自愈管线是否可靠 |
| `trace_recorder.py` | JSONL 事件记录 | 每轮 task、verification、repair、finished 都可复盘 |
| `evaluate.py` | 批量评估入口 | 汇总 challenge task 通过率、平均修复轮次、timeout 和安全拦截数量 |
| `challenge_tasks/` | 故意损坏的测试任务 | 覆盖 import、syntax、timeout、runtime/assertion、安全拦截五类问题 |
| `FUTURE_PLUGIN_ARCHITECTURE.md` | 未来插件化方向 | 只记录远期扩展思路，不属于 D-lite 当前实现范围 |

推荐阅读顺序：

```text
README.md
-> self_heal_loop.py
-> state.py
-> verification.py
-> executor.py / ast_checker.py / error_classifier.py
-> agent.py
-> evaluate.py
-> traces/*.jsonl
```

## 坑位地图

| 编号 | 坑 | 现象 | 当前处理 |
|------|-----|------|----------|
| D1 | 代码执行安全 | Agent 生成危险调用 | `ast_checker.py` 执行前拦截 |
| D2 | 错误太长 | Traceback 影响修复判断 | `error_classifier.py` 压缩尾部证据 |
| D3 | 修复循环 | 一直重试 | `max_attempts=3` |
| D4 | 环境不一致 | 原文件被污染或运行路径混乱 | 复制到 `workspaces/` 后执行 |
| D5 | 依赖错误 | 缺包或错误 import | 分类为 `import_error` |
| D6 | 执行超时 | 死循环无响应 | subprocess timeout |
| D7 | 打补丁式修复 | 改完破坏行为 | 重新运行断言验证 |
| D8 | 过度授权 | 访问宿主敏感路径 | 最小执行边界 + AST 拦截 |
| D9 | 自称成功 | Agent 文本通过但代码失败 | 只认 `verification.py` |
| D10 | Trace 缺失 | 失败无法复盘 | JSONL trace |
| D11 | 证据边界不清 | 修复理由没有绑定错误 | trace 记录错误分类和修复摘要 |

## 非目标

- 不做真实生产运维动作。
- 不做插件化运维框架。
- 不做复杂多 Agent 编排。
- 不做联网安装依赖。
- 不修改原始 challenge task。

未来插件化方向仅记录在 `FUTURE_PLUGIN_ARCHITECTURE.md`，不纳入当前实现。
