# 第二章实战任务书：GraphRAG 知识图谱增强检索

## 背景

已完成 Advanced RAG 三种模式（Baseline、Rerank、HyDE）的测评，当前要扩展第四种模式：**GraphRAG 知识图谱增强检索**。通过 LightRAG + Ollama 本地部署，将知识图谱纳入现有的 `benchmark_rag.py` 评测框架，量化对比 GraphRAG 与已有方案的效果差异。

---

## 阶段一：LightRAG 本地部署与入门（第 1 步）

**目标**：在 M4 Pro + Ollama 环境下跑通 LightRAG 最小闭环，确认它能正确从文档中提取实体和关系。

- 安装 LightRAG 及其依赖 (`pip install lightrag-hku`)
- 确认 Ollama 中已有可用模型（如 `qwen3:4b`、`nomic-embed-text`）
- 用 3-5 条测试文档运行 LightRAG 的 Indexing 流程
- 观察提取出的实体、关系和社区结构，建立对"知识图谱从文本中长什么样"的直觉

**产出**：
- [x] LightRAG 安装成功，能调用 LM Studio 完成 Indexing（2026-04-30）
- [x] 记录实体抽取结果，与原始文档对比，识别抽取的精度问题
- [x] 理解 LightRAG 的存储结构和数据文件
- [x] **总结文档已写入** `phase1_graphrag_summary.md`

> **集成的关键踩坑记录**：
> 1. Embedding 维度问题：`openai_embed` 硬编码 1536 维，但 `nomic-embed-text-v1.5` 输出 768 维 → 需自定义 embed 函数
> 2. 参数签名冲突：LightRAG 调用约定为 `llm_func(prompt, ...)`，而 `openai_complete_if_cache` 为 `(model, prompt, ...)` → 需适配层
> 3. LightRAG 1.4+ 需显式调用 `initialize_storages()`，否则抛出 `StorageNotInitializedError`

---

## 阶段二：现有数据集的全量 Indexing（第 2 步）

**目标**：将 `dataset.py` 中的 10 条测试文档灌入 LightRAG，构建完整知识图谱。

- 将 `dataset.py` 中的 `DOCUMENTS` 导入 LightRAG
- 设置 LightRAG 的 `working_dir`，持久化图谱数据
- 执行 Indexing，观察 Batch 处理时的实体合并（Merging）行为

**产出**：
- [x] 完成全量文档的图谱构建
- [x] 检查跨文档实体的合并情况（如"苹果"在不同上下文中是否被正确处理）
- [x] 记录 Indexing 耗时和 Token 消耗

---

## 阶段三：GraphRAG 检索模块集成（第 3 步）

**目标**：编写 `benchmark_graphrag.py`，将 LightRAG 检索加入现有评测框架。

- 封装 LightRAG 查询接口，支持两种检索模式：
  - **Local 检索**：只搜索与查询最相关的实体和邻居
  - **Global 检索**：查询社区摘要，回答全局性问题
- 统一输出格式：`List[doc_id]`，与现有 `benchmark_rag.py` 兼容

**产出**：
- [x] `benchmark_graphrag.py` 完成，支持独立运行
- [x] 验证单条查询能返回正确的文档 ID

---

## 阶段四：多跳推理测试集扩展（第 4 步）

**目标**：在现有语义混淆数据集的基上，补充需要"跨文档连接"的多跳推理问题。

现有 `dataset.py` 的 TEST_QUERIES 主要测试"语义混淆"场景（同一词汇在不同语境中的辨析）。GraphRAG 的优势在"连接线索"类问题，因此需要扩展：

```python
# 新增多跳测试用例示例
{
    "query": "比较1型糖尿病和2型糖尿病的病因差异",
    "expected_ids": ["B1", "B2"],  # 需要同时检索两个文档
    "difficulty": "multi-hop",
    "reason": "需要从两个文档提取信息并进行对比"
}
```

**产出**：
- [x] 新增 8 条多跳推理测试用例
- [x] 确保现有 Baseline/Rerank/HyDE 模式也能跑这些用例

---

## 阶段五：全模式对比评测（第 5 步）

**目标**：在统一框架下对比五种检索模式。

| 模式 | 说明 |
|------|------|
| Baseline | 向量检索 |
| Rerank | 向量检索 + LLM Rerank |
| HyDE | 假设文档检索 |
| HyDE+Rerank | 组合方案 |
| **GraphRAG (Local)** | 实体级图谱检索 |
| **GraphRAG (Global)** | 社区摘要级图谱检索 |

**产出**：
- [x] 在"语义混淆"测试集上的命中率对比
- [x] 在"多跳推理"测试集上的命中率对比
- [x] 各模式的延迟对比（特别是 GraphRAG 的 Indexing 摊销成本）

---

## 阶段六：总结与架构决策指南（第 6 步）

**目标**：基于实测数据，回答两个核心问题：

1. **GraphRAG 在哪些场景下值得引入？** — 量化多跳推理场景的提升幅度
2. **GraphRAG 的投入产出比是否可接受？** — 对比 Indexing 成本（时间+Token）与检索质量提升

**产出**：
- [x] 更新 `practice/summary.md`，补充 GraphRAG 评测结论
- [x] 形成"何时用向量 RAG vs 何时用 GraphRAG"的决策矩阵

---

## 附录：技术备忘录

### 关键命令行

```bash
pip install lightrag-hku
```

### LightRAG 核心 API

```python
from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc
import numpy as np

# 初始化
rag = LightRAG(
    working_dir="./graph_index",
    llm_model_func=ollama_model_complete,
    llm_model_name="qwen3:4b",
    embedding_func=EmbeddingFunc(
        func=lambda texts: ollama_embed(texts, model="nomic-embed-text"),
        max_token_size=8192,
        embedding_dim=768,
    ),
)

# Indexing
with open("docs.txt", "r") as f:
    rag.insert(f.read())

# 查询
result = rag.query("问题", param=QueryParam(mode="local"))
result = rag.query("问题", param=QueryParam(mode="global"))
```

### 注意事项

- LightRAG 目前（2026 年初）处于活跃开发中，API 可能有变动
- M4 Pro 本地运行 Qwen3-4B 做实体抽取时，需关注内存占用
- Indexing 阶段是主要耗时环节（每个 chunk 都要调 LLM），小数据集（10 条文档）预计数分钟内完成
- 首次运行后图谱持久化到磁盘，后续增量插入不会从头重建
