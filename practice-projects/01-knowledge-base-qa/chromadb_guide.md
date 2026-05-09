# ChromaDB 在知识库问答 (Project 01) 中的应用指南

## 1. 什么是 ChromaDB？

ChromaDB 是一个开源的**向量数据库**，专门为 AI 应用设计。在 RAG（检索增强生成）系统中，它的主要作用是存储文档的“向量特征”（Embeddings），并允许我们通过“语义搜索”快速找到与用户问题最相关的文档片段。

## 2. 为什么在 Project 01 中选择 ChromaDB？

*   **极简集成**：与 LlamaIndex 无缝衔接。
*   **本地运行**：无需复杂的数据库安装，数据直接以文件形式保存在磁盘上（`chroma_db/` 目录）。
*   **性能优越**：支持快速的余弦相似度计算，适合处理数千到数万个文档块。
*   **开发者友好**：支持元数据过滤，方便后续扩展权限控制或多租户功能。

---

## 3. 核心概念与代码实现

### A. 初始化持久化客户端
在 `ingestion.py` 和 `query_engine.py` 中，我们首先需要连接到数据库：

```python
import chromadb

# 设置持久化路径，确保数据关机不丢失
db = chromadb.PersistentClient(path="./chroma_db")

# 创建或获取一个集合 (Collection)，类似于关系型数据库中的表
chroma_collection = db.get_or_create_collection("kb_qa_collection")
```

### B. 适配 LlamaIndex
LlamaIndex 提供了一个 `ChromaVectorStore` 类，将 ChromaDB 的原生操作封装成统一的接口：

```python
from llama_index.vector_stores.chroma import ChromaVectorStore

# 将 Chroma 集合包装为 LlamaIndex 的向量存储
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
```

### C. 数据摄入 (Ingestion)
构建索引时，LlamaIndex 会调用 Embedding 模型将文本转化为向量，并通过 `ChromaVectorStore` 存入数据库：

```python
from llama_index.core import VectorStoreIndex, StorageContext

# 定义存储上下文
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 构建索引（会自动持久化到 chromadb 中）
index = VectorStoreIndex.from_documents(
    documents, 
    storage_context=storage_context
)
```

### D. 索引加载与查询 (Querying)
在 `query_engine.py` 中，我们不需要重新构建索引，只需从已有的 `vector_store` 加载：

```python
# 直接通过向量存储对象恢复索引
index = VectorStoreIndex.from_vector_store(vector_store)

# 创建查询引擎，设置 Top K (返回最相关的 K 个片段)
query_engine = index.as_query_engine(similarity_top_k=2)
```

---

## 4. 关键配置项说明

| 配置项 | 作用 | Project 01 中的设置 |
| :--- | :--- | :--- |
| `PersistentClient` | 指定数据保存路径 | `./practice-projects/01-knowledge-base-qa/chroma_db` |
| `Collection` | 区分不同的知识库 | `kb_qa_collection` |
| `similarity_top_k` | 检索的上下文数量 | `2` (平衡精度与 LLM 上下文限制) |

## 5. 常见问题 (FAQ)

**Q: 为什么修改了本地文档，但查询结果没变？**
A: 因为 ChromaDB 是持久化存储的。您需要再次运行 `ingestion.py` 来更新数据库。如果需要彻底重置，可以删除 `chroma_db/` 文件夹。

**Q: 检索出的内容不相关怎么办？**
A: 
1. 检查 `SentenceSplitter` 的 `chunk_size` 是否合适（本项目推荐 512）。
2. 确认 Embedding 模型（`bge-small-zh`）是否加载正确，它是决定语义检索准确度的核心。

---

> [!TIP]
> ChromaDB 默认使用内存存储，但在本项目中我们强制使用了 `PersistentClient`，这是生产环境下保证数据可靠性的标准做法。

---

## 6. 深度理解：RAG 数据管线的四个阶段

虽然代码逻辑看起来只是简单的调用，但它实际上串联起了一套完整的**生产级文档预处理流水线**。我们可以通过以下比喻来理解这些组件的设计意图：

### 第一阶段：搬运工 (Loading)
*   **组件**: `SimpleDirectoryReader`
*   **职责**: 负责把各种格式的原始文件（Markdown, PDF, Word 等）从磁盘搬进内存。
*   **产物**: 统一格式的 `Document` 对象。

### 第二阶段：手术刀 (Parsing/Chunking)
*   **组件**: `SentenceSplitter`
*   **职责**: 决定了知识的细腻程度。它不仅仅是切分，还会保留 `overlap`（重叠采样），确保语义不会在切口处因为断章取义而丢失。
*   **产物**: 切分后的 `Node` (文本块) 对象。

### 第三阶段：翻译官 (Embedding)
*   **组件**: `HuggingFaceEmbedding`
*   **职责**: 负责把人类的文字翻译成机器能听懂的“坐标（向量）”。
*   **产物**: 带有向量特征的 `Embedding` 数据。

### 第四阶段：仓库管家 (Storage & Indexing)
*   **组件**: `chromadb` & `VectorStoreIndex`
*   **职责**: `chromadb` 是物理仓库，负责在硬盘上挖坑存数据；`VectorStoreIndex` 是总管家，负责协调翻译官并将产物分门别类地存入仓库，建立起一套可以秒级检索的目录。
*   **产物**: 可供查询的持久化索引。

---

## 7. 向量数据库横向对比

在实际生产中，除了 ChromaDB，还有多种向量数据库可供选择。它们的侧重点各不相同：

| 数据库 | 类型 | 核心优势 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **ChromaDB** | 轻量级/嵌入式 | 极简、本地运行、开发者体验极佳 | 快速原型、个人/中小项目、本地化部署 |
| **Milvus** | 分布式/云原生 | 高并发、超大规模数据（亿级）、成熟稳定 | 大型企业级应用、高可用生产环境 |
| **Pinecone** | 全托管 (SaaS) | 无需运维、自动扩缩容、上手即用 | 希望省去运维成本、云端原生 AI 应用 |
| **Weaviate** | 语义对象存储 | 支持混合查询（向量+关键词+属性）、自带 GraphQL | 复杂数据关联、需要丰富元数据检索的场景 |
| **PGVector** | 插件式 (Postgres) | 兼容已有生态、事务支持、无需增加新组件 | 已有 Postgres 数据库、数据一致性要求高 |

**选择建议：** 如果是学习或中小规模 RAG，**ChromaDB** 是首选；如果是追求海量数据和高性能，建议转向 **Milvus** 或 **Pinecone**。

---

## 8. 文档切分标准与关联关系保持

在 Project 01 中，我们将长文档切分为多个 Chunk，但这会带来一个问题：**切分后语义可能断裂**。以下是保持关联关系的常用标准和策略：

### A. 切分标准 (Chunking Strategy)
*   **固定长度切分 (Fixed-size)**：最简单，但容易切断句子。
*   **语义边界切分 (Sentence/Paragraph)**：本项目采用的方式（`SentenceSplitter`），优先在句号、换行符处切分。
*   **启发式切分**：识别 Markdown 标题（H1-H3），保持章节的完整性。

### B. 如何保持关联关系？

1.  **重叠 (Overlap)**：
    *   在相邻的 Chunk 之间保留一定的重叠部分（如 `chunk_overlap=50`）。
    *   **作用**：确保上一个 Chunk 的结尾信息出现在下一个 Chunk 的开头，提供必要的上下文连续性。

2.  **元数据回链 (Metadata Linking)**：
    *   在存储每个 Chunk 时，将 `file_name`、`parent_doc_id`、`page_number` 等信息存入 ChromaDB 的元数据中。
    *   **作用**：检索到某个 Chunk 后，可以立即根据元数据找到其所属的完整文档或前后章节。

3.  **父子块策略 (Parent-Child Retriever)**：
    *   **思路**：将文档切分为“小块”（用于检索，匹配更精准）和“大块”（作为上下文发送给 LLM）。
    *   **实现**：数据库中存储小块，但元数据指向其所属的大块 ID。检索到小块后，自动加载其关联的大块。

4.  **摘要增强 (Contextual Summarization)**：
    *   在每个 Chunk 的头部增加文档的标题或全局摘要。
    *   **作用**：即使 Chunk 位于文档深处，也带有“身份信息”，防止模型在生成答案时“迷失”。

---

> [!IMPORTANT]
> **切分不是越细越好**。太细会导致语义碎片化，太粗会导致检索出的噪音过多。在 Project 01 中，我们选择 **512 Token + 50 Overlap** 是一个经过验证的经验平衡点。
