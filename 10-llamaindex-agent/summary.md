# 阶段 10 总结：LlamaIndex 数据中心型 Agent

> 状态：已完成
> 本文是阶段复盘总结。已完成 `llamaindex_agent.py` 的编写与真实环境运行验证。

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

- 依赖安装成功，包含 `llama-index-core`、`llama-index-llms-openai-like` 等。
- 验证了 `FunctionAgent` 在 OpenAI 兼容模式下的工具调用稳定性。

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

运行脚本：`venv/bin/python 10-llamaindex-agent/llamaindex_agent.py`

**Agent 最终回答（节选）：**

> 根据学习文档，LlamaIndex 和 LangGraph 的核心分工如下：
> 
> **LlamaIndex 的核心职责：**
> 1. 数据接入与索引构建 - 专门处理各种数据源的接入和索引创建
> 2. 检索功能 - 提供强大的文档检索能力
> 3. 知识库问答 - 特别适合处理复杂文档和知识库的问答场景
> 
> **LangGraph 的核心职责：**
> 1. 状态管理 - 专注于智能体状态的管理和维护
> 2. 流程控制 - 通过图结构定义执行路径和循环逻辑
> 
> 简单来说：**LlamaIndex 是"数据专家"，LangGraph 是"流程专家"**。

**工具调用验证：**
当询问“你加载了哪些学习文档？”时，Agent 成功调用了 `list_loaded_documents` 自定义函数工具，返回了：
1. concept.md
2. summary.md

---

## 五、与阶段 05 Self-RAG 对比

待补充：安装依赖并运行示例后，与 `05-final-project/` 的 LangGraph Self-RAG 对比。

建议从这些角度比较：

| 维度 | LlamaIndex 示例 | LangGraph Self-RAG |
| :--- | :--- | :--- |
| 数据接入 | 极简：`SimpleDirectoryReader` 几行代码搞定 | 较复杂：需手动处理加载与切分 |
| 索引与检索 | 原生集成：`VectorStoreIndex` 支持多种检索策略 | 需配合向量数据库：如 Chroma/FAISS 需手动编排 |
| 状态管理 | 隐式：由 Agent 框架内部管理（Workflow 模式） | 显式：由开发者定义 State 结构 |
| 流程控制 | 事件驱动或自动循环（FunctionAgent） | 图结构：显式定义 Node 和 Edge |
| 可观测性 | 深度集成：LlamaTrace 等 | 灵活：需集成 LangSmith 等 |
| 适用场景 | 快速构建知识库问答、复杂数据 RAG | 复杂逻辑编排、多 Agent 协作、审批流 |

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

- **LlamaIndex 解决了数据工程问题**：它将复杂的文档解析、分块、向量化和检索封装成标准组件，极大降低了 RAG 系统的开发门槛。
- **职责边界清晰**：LlamaIndex 负责“数据检索与知识合成”；LangGraph 负责“任务编排与状态流转”。
- **选型与组合**：
    - 简单的知识库助手优先用 LlamaIndex。
    - 具有复杂判断逻辑、需要人工介入或多步骤循环的任务优先用 LangGraph。
    - **黄金组合**：在 LangGraph 的 Node 中调用 LlamaIndex 的 Query Engine 作为子任务执行器。
