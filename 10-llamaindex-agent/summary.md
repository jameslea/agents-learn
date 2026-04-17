# 阶段 10 总结：LlamaIndex 数据中心型 Agent

> 状态：未完成
> 本文是阶段复盘模板。完成 `llamaindex_agent.py` 后，再回填实际代码观察、运行结果和阶段结论。

---

## 一、阶段目标

本阶段目标是完成一个 LlamaIndex 数据中心型 Agent 的最小闭环：

```text
读取本地学习文档
  -> 构建索引
  -> 创建 Query Engine
  -> 包装为工具
  -> 让 Agent 调用工具回答问题
```

概念背景见：[LlamaIndex 入门：数据中心型 Agent](./concept.md)。

---

## 二、已完成实验

已完成最小示例脚本：[llamaindex_agent.py](./llamaindex_agent.py)。

当前实验内容：

- 使用 `SimpleDirectoryReader` 读取本目录下的 `concept.md` 和 `summary.md`。
- 使用 `VectorStoreIndex` 构建学习文档索引。
- 使用 `MockEmbedding(embed_dim=1536)` 避免索引阶段产生 embedding API 成本。
- 使用 `QueryEngineTool` 将 Query Engine 包装为 Agent 工具。
- 使用 `FunctionAgent` 作为阶段 10 的最小数据中心型 Agent。
- 额外提供 `list_loaded_documents` 函数工具，用于观察当前索引加载了哪些文档。

待补充：

- 安装 LlamaIndex 依赖后，记录完整运行输出。
- 根据真实运行情况确认当前版本 API 是否需要调整。

---

## 三、核心代码观察

当前代码结构：

- `require_llamaindex_imports()`：延迟导入 LlamaIndex，并在缺依赖时给出清晰安装提示。
- `create_llm()`：复用项目已有 `.env` 约定，读取 `MODEL_NAME`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`。
- `build_query_engine()`：加载本地学习文档、设置 `MockEmbedding`、构建 `VectorStoreIndex` 和 Query Engine。
- `create_agent()`：把 Query Engine 包装成 `QueryEngineTool`，并组装 `FunctionAgent`。
- `main()`：运行默认问题，也支持通过 `LLAMAINDEX_DEMO_QUESTION` 环境变量替换问题。

这个结构刻意保持线性，便于学习者对应 LlamaIndex 的核心链路：

```text
Document -> Index -> Query Engine -> Tool -> Agent
```

---

## 四、运行结果

当前已完成语法级验证：

```text
venv/bin/python -m py_compile 10-llamaindex-agent/llamaindex_agent.py
```

结果：通过。

在未安装 LlamaIndex 依赖时运行：

```text
venv/bin/python 10-llamaindex-agent/llamaindex_agent.py
```

脚本会给出明确提示：

```text
缺少 LlamaIndex 依赖。请先运行：
  pip install -r requirements.txt
```

待补充：安装依赖并配置模型后，记录真实 Agent 输出。

---

## 五、与阶段 05 Self-RAG 对比

待补充：安装依赖并运行示例后，与 `05-final-project/` 的 LangGraph Self-RAG 对比。

建议从这些角度比较：

| 维度 | LlamaIndex 示例 | LangGraph Self-RAG |
| :--- | :--- | :--- |
| 数据接入 | 待补充 | 待补充 |
| 索引与检索 | 待补充 | 待补充 |
| 状态管理 | 待补充 | 待补充 |
| 流程控制 | 待补充 | 待补充 |
| 可观测性 | 待补充 | 待补充 |
| 适用场景 | 待补充 | 待补充 |

---

## 六、踩坑与兼容性记录

当前记录：

- 当前工具 shell 未激活虚拟环境，因此所有检查命令都显式使用 `venv/bin/python`。
- 本地 `venv` 初始未安装 LlamaIndex，联网安装依赖未执行完成。
- 示例代码已经做了延迟导入和缺依赖提示，避免直接抛出难读的低层 `ImportError`。

后续仍需验证：

- `llama-index-llms-openai-like` 包名和当前 LlamaIndex 版本兼容性。
- DeepSeek / OpenAI-compatible endpoint 下 `FunctionAgent` 的工具调用行为。
- `MockEmbedding` 对检索质量的影响。

---

## 七、阶段结论

待补充：完成阶段 10 后填写。

最终应该回答：

- LlamaIndex 在数据中心型 Agent 中解决了什么问题？
- 它和 LangGraph 的职责边界是什么？
- 什么场景优先选择 LlamaIndex？
- 什么场景更适合 LangGraph 作为主控？
- 两者如何组合到一个生产级 Agent 系统里？
