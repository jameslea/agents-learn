# 阶段 12：自主任务循环 Agent

> 状态：✅ 已完成

本阶段手写了一个 BabyAGI 风格的最小自主任务系统，理解 AutoGPT 类框架背后的任务队列、执行、反思和停止机制。并使用 LangGraph 状态图进行了工业级重构。

---

## 核心学习成果

- BabyAGI 的三环结构：任务执行 → 任务生成 → 任务排序
- 自主循环中的关键挑战：目标漂移、无限循环、成本不可控
- 工程化约束：Max Loops、Human-in-the-loop、Pydantic 结构化输出
- 原生 `while` 循环 vs LangGraph 状态图两种实现方式的对比
- 详见：[concept.md](./concept.md) 与 [summary.md](./summary.md)

---

## 代码文件

| 文件 | 说明 |
|---|---|
| `babyagi_native.py` | 原生手写 `while` 循环版本的 BabyAGI，直观展示三环结构 |
| `babyagi_langgraph.py` | 使用 LangGraph 状态图框架重构的工业级稳健版本 |

---

## 运行示例

```bash
# 原生版本
venv/bin/python 12-autonomous-agents/babyagi_native.py

# LangGraph 版本
venv/bin/python 12-autonomous-agents/babyagi_langgraph.py
```

---

## 阶段总结

详见 [summary.md](./summary.md)。
