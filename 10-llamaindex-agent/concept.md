# LlamaIndex 入门：数据中心型 Agent

> 本文是阶段 10 的概念预习文档。目标是先理解 LlamaIndex 的定位、核心概念和学习路径，再开始编写示例代码。

---

## 一、LlamaIndex 是什么

LlamaIndex 是一个偏“数据中心型”的 LLM / Agent 框架。它的核心定位是：帮助开发者构建“基于你的数据”的 LLM 应用、RAG 系统、Agent 和 Workflow。

它最擅长的不是复杂状态机编排，而是把企业内部文档、PDF、网页、数据库、结构化 / 非结构化数据变成 LLM 可以检索、理解和推理的上下文。

一句话理解：

```text
LangGraph 更像 Agent 工作流引擎
LlamaIndex 更像 Agent 的数据接入、索引和检索引擎
```

当然，LlamaIndex 现在也不只是 RAG 框架。它也提供 Agent、Tools、Workflows、多 Agent、LlamaParse、LlamaCloud 等能力。但它的核心优势仍然围绕“数据”展开。

---

## 二、它解决什么问题

典型 LLM 应用会遇到一个现实问题：模型本身不知道你的私有数据。

比如：

- 公司内部文档
- 产品手册
- 财报
- 会议纪要
- PDF 合同
- 代码库
- 数据库记录

LlamaIndex 负责把这些数据接入、切分、索引、检索，并在用户提问时把相关内容交给 LLM。

最基础流程是：

```text
Documents
  -> Load
  -> Parse / Chunk
  -> Index
  -> Retrieve
  -> Query Engine / Agent
  -> Answer
```

这也是 LlamaIndex 最值得学习的地方：它把“数据如何进入 Agent”这件事工程化了。

---

## 三、核心概念

### 1. Document

`Document` 是原始数据对象。

它可以来自一个 Markdown 文件、PDF 页面、网页内容、数据库记录，或者其他数据源。

### 2. Node

`Node` 是文档切分后的更小语义块。

RAG 系统通常不会把整篇文档直接塞给模型，而是先切成更适合检索和拼接的片段。

### 3. Index

`Index` 是索引结构。

最常见的是向量索引 `VectorStoreIndex`。它会把文档片段转成向量，方便后续根据语义相似度检索。

### 4. Retriever

`Retriever` 负责根据用户问题，从索引中找出相关片段。

它决定了“哪些上下文会被送进模型”，因此直接影响回答质量。

### 5. Query Engine

`Query Engine` 是面向问答的封装。

它通常会完成：

```text
用户问题 -> 检索相关内容 -> 组织上下文 -> 调用 LLM -> 生成答案
```

最小 RAG 示例通常会从 Query Engine 开始。

### 6. Tool

`Tool` 是 Agent 可调用的能力。

LlamaIndex 很有意思的一点是：一个 Query Engine 也可以包装成 Tool。这样 Agent 就可以在多个知识库工具之间选择。

### 7. Agent

LlamaIndex 中的 Agent 是一个可以自动推理和决策的执行单元。

它可以：

- 理解用户问题
- 拆解任务
- 选择工具
- 调用 Query Engine
- 综合多个结果
- 判断是否继续执行

### 8. Workflow

`Workflow` 是 LlamaIndex 的事件驱动编排抽象。

它可以用来构建 RAG 流程、Agent 流程、信息抽取流程，或者更复杂的自定义工作流。

---

## 四、和 LangGraph 的区别

LlamaIndex 和 LangGraph 不是二选一关系，它们更像是互补关系。

| 维度 | LlamaIndex | LangGraph |
| :--- | :--- | :--- |
| 核心优势 | 数据接入、索引、检索、Agentic RAG | 状态机、节点、边、循环、可控编排 |
| 思维方式 | 数据先行：文档如何变成上下文 | 流程先行：任务如何按状态流转 |
| 典型入口 | `Document -> Index -> QueryEngine -> Agent` | `State -> Node -> Edge -> Graph` |
| 适合场景 | 企业知识库、文档问答、复杂检索、多数据源问答 | 多步骤 Agent、Self-RAG、审批流、多 Agent 调度 |
| 组合方式 | 可作为 LangGraph 节点里的检索 / 查询能力 | 可作为外层总控调用 LlamaIndex |

所以阶段 10 最值得研究的不是“用 LlamaIndex 替代 LangGraph”，而是理解：

```text
LlamaIndex 负责让 Agent 更懂数据
LangGraph 负责让 Agent 更可控地做事
```

这两个框架可以组合，而不是互相替代。

---

## 五、为什么值得单独学

当前仓库已经完成了阶段 05 的 LangGraph Self-RAG，但那里的数据层仍然比较简化。

LlamaIndex 可以帮助我们继续研究更真实的数据问题：

- 多文档、多目录、多数据源如何接入？
- PDF、网页、Markdown、数据库如何统一处理？
- 检索质量如何提升？
- 如何让 Agent 在多个知识库工具之间选择？
- 如何做 Agentic RAG，而不是简单“检索一次就回答”？
- 如何从 Query Engine 进化到 Agent Workflow？

也就是说，阶段 10 的重点不是“多学一个框架”，而是补上 Agent 系统里的数据层能力。

---

## 六、推荐学习资源

优先看官方资料：

1. [LlamaIndex 官方文档首页](https://docs.llamaindex.ai/)
   - 最好的入口，包含 Quickstart、Python / TypeScript、Use Cases、LlamaCloud 等。

2. [LlamaIndex Agents 文档](https://docs.llamaindex.ai/en/stable/use_cases/agents/)
   - 重点看 Agent 的定义、适用场景、Prebuilt Agents、Tools、Agentic RAG、Workflows。

3. [Building an agent](https://docs.llamaindex.ai/en/stable/understanding/agent/)
   - 适合进入阶段 10 前阅读，重点理解 Agent 如何选择工具、循环执行、判断任务是否完成。

4. [LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/workflows/)
   - 重点理解事件驱动 Workflow。这个方向适合和 LangGraph 对比。

5. [LlamaIndex GitHub](https://github.com/run-llama/llama_index)
   - 看源码、examples、issues 和版本变化。后续写示例时应以官方最新 API 为准。

6. [LlamaIndex Cloud / LlamaParse](https://www.llamaindex.cloud/)
   - 了解它的商业产品线，尤其是文档解析、OCR、复杂 PDF、表格和企业文档自动化场景。

---

## 七、阶段 10 建议学习顺序

建议按下面的节奏推进：

```text
最小 RAG
  -> Query Engine 作为 Tool
  -> FunctionAgent
  -> Agentic RAG
  -> 与 LangGraph Self-RAG 对比
```

### 1. 最小 RAG

先跑通最基础路径：

```text
SimpleDirectoryReader -> VectorStoreIndex -> query_engine
```

目标是理解 LlamaIndex 如何读取文档、建立索引和回答问题。

### 2. Query Engine 作为 Tool

把一个知识库问答能力包装成 Agent 工具。

目标是理解“知识库本身也可以成为 Agent 的工具”。

### 3. FunctionAgent

让 Agent 在普通函数工具和 Query Engine 工具之间选择。

目标是理解 LlamaIndex Agent 的工具选择机制。

### 4. Agentic RAG

不只是检索一次，而是让 Agent 根据问题决定是否继续查询、换工具、综合答案。

目标是理解 Agentic RAG 和普通 RAG 的区别。

### 5. 与 LangGraph Self-RAG 对比

最后写一篇总结，对比阶段 10 和阶段 05：

- LlamaIndex 更擅长什么？
- LangGraph 更擅长什么？
- 两者如何组合？
- 真实项目里如何选型？

---

## 八、阶段目标

阶段 10 的目标不是全面掌握 LlamaIndex，而是完成“数据中心型 Agent”的最小闭环。

完成本阶段后，应该能够回答：

- LlamaIndex 和 LangGraph 的核心区别是什么？
- 为什么 LlamaIndex 更适合处理复杂数据接入和检索？
- Query Engine、Retriever、Agent、Workflow 分别负责什么？
- 如何用 LlamaIndex 构建一个最小知识库问答 Agent？
- 如何把 LlamaIndex 作为 LangGraph 工作流里的数据能力？
