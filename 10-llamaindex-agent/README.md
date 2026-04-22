# 阶段 10：LlamaIndex 数据中心型 Agent

> 状态：✅ 已完成

本阶段计划研究 LlamaIndex 在数据接入、索引、Query Engine 和 Agentic RAG 中的优势，并与阶段 05 的 LangGraph Self-RAG 进行对比。

## 学习文档

- [LlamaIndex 入门：数据中心型 Agent](./concept.md)
- [阶段 10 总结：LlamaIndex 数据中心型 Agent](./summary.md)

## 计划内容

- Document、Node、Index、Query Engine 的基础概念。
- FunctionAgent / AgentWorkflow 的最小示例。
- LlamaIndex 风格 RAG 与 LangGraph Self-RAG 的差异。
- 企业知识库问答中的数据治理问题。

## 运行示例

阶段 10 的最小示例会读取本目录下的 `concept.md` 和 `summary.md`，构建一个本地学习文档索引，再让 LlamaIndex `FunctionAgent` 通过 `QueryEngineTool` 查询这些学习资料。

```bash
venv/bin/pip install -r requirements/phase10-llamaindex.txt
venv/bin/python 10-llamaindex-agent/llamaindex_agent.py
```

默认问题是：

```text
LlamaIndex 和 LangGraph 的核心分工是什么？
```

可以通过环境变量替换问题：

```bash
LLAMAINDEX_DEMO_QUESTION="LlamaIndex 的 Query Engine 是什么？" \
venv/bin/python 10-llamaindex-agent/llamaindex_agent.py
```

## 预计产物

- `llamaindex_agent.py`
- `concept.md`
- `summary.md`
