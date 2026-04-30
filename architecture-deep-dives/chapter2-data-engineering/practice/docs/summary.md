# 第二章：深度数据工程 —— 实战总结

## 实战文件结构

```
practice/
├── code/                              # 代码
│   ├── dataset.py                     # 数据集：10条文档 + 6条单跳 + 8条多跳查询
│   ├── lm_studio_llm.py               # LM Studio 适配层（LLM + Embedding）
│   ├── benchmark_rag.py               # 向量模式评测：Baseline / Rerank / HyDE / HyDE+Rerank
│   ├── benchmark_graphrag.py          # GraphRAG 评测：Local / Global
│   ├── phase2_build_graph.py          # LightRAG 图谱构建（全量/调试模式）
│   ├── test_lightrag_lmstudio.py      # LightRAG 连通性测试
│   └── phase5_comparison.py           # 统一对比表生成
├── data/                              # 图谱数据 + 评测结果
│   ├── graph_index_dataset/           # 全量文档图谱（12 个文件）
│   ├── graph_index_test/              # 阶段一测试图谱（12 个文件）
│   ├── results_benchmark_single.json  # 向量模式单跳测试结果
│   ├── results_benchmark_multi.json   # 向量模式多跳测试结果
│   └── graphrag_benchmark_results.json# GraphRAG 评测结果
└── docs/                              # 文档
    ├── summary.md                     # ← 本文：最终总结与决策矩阵
    ├── rerank_deep_dive.md            # Rerank 技术复盘
    ├── vector_search_fundamentals.md  # 向量检索基础指南
    ├── phase1_graphrag_summary.md     # GraphRAG 阶段一总结
    └── TODO_GRAPH.md                  # GraphRAG 任务跟踪
```

## 核心结论速览

| 场景 | 推荐方案 | 命中率 |
|------|---------|-------|
| 同义/近义检索 | Baseline | 83% (0.02s) |
| 语义混淆（一词多义） | **HyDE** / **HyDE+Rerank** | **100%** |
| 多跳推理（跨文档连接） | **HyDE+Rerank** | **88%** |
| 多跳推理（稳定数据，Indexing 后） | **GraphRAG-Global** | 75% (0.1s) |
| 全局总结 | GraphRAG-Global | 唯一可行方案 |
| 低延迟实时系统 | Baseline / GraphRAG（缓存命中） | 83% / 75% (<0.1s) |

## 任务背景

本章实战围绕"高级检索增强"展开，分两个阶段：

**阶段一（Advanced RAG）**：在语义混淆数据集上对比 Baseline（向量检索）、Rerank（LLM 重排）、HyDE（查询扩展）、HyDE+Rerank 四种模式，验证各自在处理"一词多义"时的真实威力。

**阶段二（GraphRAG）**：引入知识图谱增强检索，新增多跳推理测试集，最终完成全部六种模式（+GraphRAG-Local/Global）的统一对比。

详见 `TODO_GRAPH.md` 各阶段记录。

## 1. 数据集

| 维度 | 说明 |
|------|------|
| 文档数 | 10 条，覆盖 8 个主题（科技、美食、农业、科学史、医学×2、编程、法律、地理×2） |
| 语义混淆 | 同一词汇在不同语境（如"苹果"→公司/食材/病害/科学） |
| 多跳推理 | 8 条，需要跨文档连接信息才能回答（如"比较 1 型和 2 型糖尿病"） |

## 2. 六种检索模式对比

### 2.1 单跳测试集（语义混淆，6 条查询）

| 模式 | 命中率 | 平均延迟 | 典型失败原因 |
|------|--------|---------|------------|
| Baseline | 83% (5/6) | 0.02s | "苹果手机"命中 A1 失败（向量偏差） |
| Rerank (LLM) | 83% (5/6) | 3.46s | 同 Baseline，粗排漏了精排也无力 |
| HyDE | **100% (6/6)** | 5.88s | - |
| HyDE+Rerank | **100% (6/6)** | 4.44s | - |
| GraphRAG-Local | 50% (3/6) | 0.1s* | 实体级检索不分语境，"苹果"映射到错误实体 |
| GraphRAG-Global | 83% (5/6) | 7.3s* | 社区摘要覆盖面广，但仍有个别盲区 |

\* GraphRAG 延迟含 Indexing 摊销（全量构建约 10min），查询本身秒级。

### 2.2 多跳测试集（连接线索，8 条查询）

| 模式 | 命中率 | 平均延迟 | 典型失败原因 |
|------|--------|---------|------------|
| Baseline | 38% (3/8) | 0.06s | Top-3 向量检索只能命中单个文档 |
| Rerank (LLM) | 75% (6/8) | 4.05s | 精排能从 Top-5 中捞出第二个文档 |
| HyDE | 62% (5/8) | 5.80s | 假设文档偏向单一上下文，丢失多文档视角 |
| HyDE+Rerank | **88% (7/8)** | 6.17s | 组合策略最稳健 |
| GraphRAG-Local | 75% (6/8) | 26.5s | 图谱结构连接跨文档实体 |
| GraphRAG-Global | 75% (6/8) | 26.0s | 同上，社区摘要辅助 |

### 2.3 关键发现

```
                    语义混淆         多跳推理
Baseline            83%    →         38%    ▼▼▼
HyDE+Rerank         100%   →         88%    ▼
GraphRAG-Global     83%    →         75%    =
```

- **HyDE+Rerank 综合最强** — 两个测试集上都接近满分，适合通用场景
- **GraphRAG 的抗衰减性最强** — 从单跳到多跳的命中率降幅最小（83%→75%），在向量 Baseline 暴跌至 38% 时依然稳定
- **没有银弹** — HyDE 在多跳场景从 100% 降至 62%，GraphRAG 在语义混淆场景只有 50%（Local）

## 3. 决策矩阵：何时用哪种方案

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| **简单问答**（单文档事实） | Baseline（或跳过检索直接 LLM） | 延迟毫秒级，命中率已够 |
| **语义混淆**（一词多义） | **HyDE** | 100% 命中率，延迟可接受 |
| **多跳推理**（跨文档连接） | **HyDE+Rerank** 或 **GraphRAG** | HyDE+Rerank 88% 最高；GraphRAG 75% 但 Indexing 后查询稳定 |
| **全局总结**（全库概览） | **GraphRAG-Global** | 社区摘要直接输出全局视角，其他模式做不到 |
| **高召回需求**（命中性优先） | **HyDE+Rerank** | 两个测试集平均 94%，最接近无误检 |
| **低延迟需求**（实时系统） | **Baseline**（<0.1s）或 **GraphRAG**（Indexing 后 0.1-0.3s） | 缓存命中时 GraphRAG 查询极快 |
| **冷启动 / 快速原型** | Baseline → HyDE → Rerank（渐进式叠加） | GraphRAG 的 Indexing 成本高，适合稳定数据 |

## 4. 工程启示

### 4.1 延迟与精度的本质权衡

```
精度
  ↑
  │     HyDE+Rerank (88%, 6s)
  │     Rerank (75%, 4s)   GraphRAG (75%, 26s)
  │     HyDE (62%, 6s)
  │     Baseline (38%, 0.06s)
  └─────────────────────────────→ 延迟
```

多跳场景下，精度每提升 10 个百分点，延迟约翻 10 倍。

### 4.2 GraphRAG 的适用条件

GraphRAG 不是通用的 RAG 替代方案，它有明确的适用边界：

| 适合引入 GraphRAG | 不适合引入 GraphRAG |
|------------------|-------------------|
| 数据稳定（Indexing 可复用） | 数据频繁变化 |
| 需要跨文档连接线索 | 答案集中在单文档 |
| 有全局总结需求 | 只需简单事实问答 |
| 能接受 Indexing 成本 | 需要秒级上线 |

### 4.3 LLM Cache 的战略价值

GraphRAG 的 LLM Cache（本次实测 46 条缓存，289KB）将二次查询从 40-50s 压缩到 0.1s。对于稳定知识库，Indexing 的一次性投入可以通过缓存反复摊销。

---

**核心结论**：数据工程决定检索下限，检索策略决定回答上限。没有一种方案适配所有场景，理解各自的优势区间比追求单一方案的极致更重要。
