# GraphRAG 阶段一总结：LightRAG + LM Studio 集成

> 对应 TODO_GRAPH.md 阶段一，已完成。

---

## 1. 整体架构

```
test_lightrag_lmstudio.py (入口)
        │
        ▼
lm_studio_llm.py (适配层)
  ├── lm_studio_complete()  →  LightRAG 调用 LLM 进行实体抽取、摘要、查询
  └── lm_studio_embed()     →  LightRAG 调用 Embedding 进行向量化
        │
        ▼
LM Studio (本地推理引擎)
  ├── qwen/qwen3-4b-2507   →  LLM 推理（实体抽取、关系识别、社区摘要、查询回答）
  └── text-embedding-nomic-embed-text-v1.5 → 文本向量化
```

**为什么需要适配层？**

LightRAG 内部调用 LLM 的约定是 `llm_func(prompt, system_prompt=..., history_messages=...)`，即**第一个位置参数是 prompt**。而 OpenAI SDK 的 `openai_complete_if_cache` 签名是 `(model, prompt, ...)`，**第一个位置参数是 model**。适配层负责转换参数顺序和过滤 LightRAG 内部参数（如 `hashing_kv`、`_priority`），避免传递给 LM Studio。

---

## 2. 代码文件解析

### `lm_studio_llm.py` — LM Studio 适配器（被调用方）

两个核心函数：

| 函数 | 功能 | 关键细节 |
|------|------|---------|
| `lm_studio_complete()` | LLM 推理调用 | 过滤 `hashing_kv`、`_priority` 等 LightRAG 内部参数；固定使用 `qwen3-4b` |
| `lm_studio_embed()` | 文本向量化 | 通过 `@wrap_embedding_func_with_attrs` 装饰器声明维度 768（nomic-embed-text 的输出维度） |

### `test_lightrag_lmstudio.py` — 测试入口（主动调用方）

执行流程（共 3 步）：

```
[Step 1] 初始化存储
   → rag.initialize_storages()
   → 创建 12 个数据文件（见第 3 节）

[Step 2] 插入文档（3 条新能源汽车相关短文）
   → rag.ainsert(doc) × 3
   → LightRAG 异步 pipeline 自动执行：
      文本分块 → 实体抽取 → 关系抽取 → 实体合并 → 向量化 → 写盘
   → 日志看到 "Chunk 1 of 1 extracted X Ent + Y Rel" 表示抽取完成

[Step 3] 查询测试（2 种模式）
   │
   ├── Local 模式: 实体级检索
   │   逻辑: 从查询中提取关键词 → 匹配图中实体 → 获取邻居和关联 chunk → LLM 生成回答
   │   适用: 精确事实问答（如"特斯拉和谁有合作？"）
   │
   └── Global 模式: 社区摘要级检索
       逻辑: 提取高层关键词 → 匹配社区摘要（多个实体的聚合信息）→ LLM 生成全局总结
       适用: 全局概括性问题（如"电池供应商有哪些？"）
```

**关键配置参数：**

```python
rag = LightRAG(
    working_dir="graph_index_test/",      # 数据持久化目录
    llm_model_func=lm_studio_complete,     # LLM 函数
    embedding_func=EmbeddingFunc(...),     # 向量化函数（维度 768）
    llm_model_max_async=1,                 # 串行 LLM 调用（避免 LM Studio 过载）
    enable_llm_cache=True,                 # 缓存 LLM 结果，重复运行节省时间
)
```

---

## 3. 数据文件说明（graph_index_test/）

### KV 存储（键值对，JSON 格式）

| 文件 | 大小 | 内容 |
|------|------|------|
| `kv_store_full_docs.json` | 1KB | 原始文档全文 |
| `kv_store_text_chunks.json` | 2KB | 文本分块结果（按 token 切段） |
| `kv_store_full_entities.json` | 1KB | 每篇文档提取的实体名列表 |
| `kv_store_full_relations.json` | 1KB | 每篇文档提取的关系对列表 |
| `kv_store_entity_chunks.json` | 2KB | 实体与文本块的关联映射 |
| `kv_store_relation_chunks.json` | 2KB | 关系与文本块的关联映射 |
| `kv_store_doc_status.json` | 2KB | 文档处理状态（已处理/处理中） |
| `kv_store_llm_response_cache.json` | 101KB | **LLM 调用缓存**（最大文件，所有实体抽取+查询的 LLM 响应） |

### 向量存储（NanoVectorDB，用于语义搜索）

| 文件 | 大小 | 说明 |
|------|------|------|
| `vdb_entities.json` | 63KB | 实体的 Embedding 向量库 |
| `vdb_relationships.json` | 50KB | 关系的 Embedding 向量库 |
| `vdb_chunks.json` | 19KB | 文本块的 Embedding 向量库 |

### 图谱存储

| 文件 | 大小 | 说明 |
|------|------|------|
| `graph_chunk_entity_relation.graphml` | 8KB | **核心图谱数据**（节点=实体，边=关系，可导入 Neo4j/NetworkX 可视化） |

---

## 4. 手动执行与观察指南

### 执行命令

```bash
cd architecture-deep-dives/chapter2-data-engineering/practice

# 确保 venv 激活 && LM Studio 已运行
source ../../venv/bin/activate
python3 test_lightrag_lmstudio.py
```

### 运行中观察什么

**阶段一：初始化日志**

```
Created new empty graph file: ...graph_chunk_entity_relation.graphml
Init ... vdb_entities.json 0 data
Init ... vdb_relationships.json 0 data
Init ... vdb_chunks.json 0 data
KV load ... with 0 records  (×8 种 KV 存储)
```

→ 确认所有存储文件已创建。`0 data` 表示空库，正常。

**阶段二：文档插入日志**

```
Processing d-id: doc-xxx
== LLM cache == saving: default:extract:hash    ← 实体抽取结果
== LLM cache == saving: default:extract:hash    ← 关系抽取结果
Chunk 1 of 1 extracted 4 Ent + 3 Rel            ← 该文档提取了 4 个实体、3 个关系

Merging stage 1/1
Phase 1: Processing 4 entities ...
Phase 2: Processing 3 relations ...
Merged: `Tesla` | 1+1                           ← 实体合并（Tesla 跨文档出现两次）
Completed merging: 4 entities, 0 extra entities, 3 relations
Writing graph with 10 nodes, 8 edges            ← 最终图谱规模
```

**阶段三：查询日志**

```
Query nodes: Tesla, Battery supplier           ← Local: 提取的关键词
Local query: 10 entites, 8 relations
After truncation: 10 entities, 8 relations     ← 截断后的上下文
Final context: 10 entities, 8 relations, 3 chunks
== LLM cache == saving: local:query:hash       ← 查询结果缓存
```

### 运行后如何检查结果

**查看图谱结构：**
```bash
# 查看所有实体
python3 -c "import json; d=json.load(open('graph_index_test/kv_store_full_entities.json')); [print(k, v['entity_names']) for k,v in d.items()]"

# 查看所有关系
python3 -c "import json; d=json.load(open('graph_index_test/kv_store_full_relations.json')); [print(k, v['relation_pairs']) for k,v in d.items()]"
```

**查看原始输入输出：**
```bash
# 原始文档
cat graph_index_test/kv_store_full_docs.json

# 实体抽取缓存（LLM 原始输出）
python3 -c "
import json
d=json.load(open('graph_index_test/kv_store_llm_response_cache.json'))
for k,v in list(d.items())[:3]:
    print(f'--- {k} ---')
    print(v['return'])
"
```

**可视化图谱：** 可将 `graph_chunk_entity_relation.graphml` 导入 [Graphviz](https://graphviz.org/) 或 [Neo4j 浏览器](https://neo4j.com/product/auradb/) 查看。

---

## 5. 阶段一关键发现

| 维度 | 结论 |
|------|------|
| **集成可行性** | LightRAG + LM Studio (OpenAI 兼容接口) 完全可工作，适配层仅需处理参数签名 |
| **实体抽取质量** | Qwen3-4B 能正确识别领域实体，但实体名偏向英文输出 |
| **实体合并** | 同名实体跨文档自动合并（"Tesla"出现两次→合并为一个节点） |
| **指代消解** | CATL 和 Ningde Times（同一实体的中英文）未被合并，需外部实体对齐 |
| **查询质量** | Local 模式精确，Global 模式可做跨文档总结但依赖社区摘要质量 |
| **LLM Cache 价值** | 101KB 缓存避免重复调用 LLM，重复运行秒出结果 |
| **运行时间** | 3 条文档 + 2 次查询 ≈ 1-2 分钟（主要花在 LLM 推理上） |

---

## 6. 下一步

进入**阶段二**：将 `dataset.py` 中的 10 条语义混淆文档全量灌入 LightRAG，构建完整知识图谱，观察跨领域实体的抽取和合并效果。
