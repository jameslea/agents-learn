# 项目 01：企业知识库问答系统 (Knowledge Base QA)

## 场景描述
针对企业内部文档（制度、方案、会议纪要）的精准问答，重点在于解决语义混淆和长文本分块导致的检索失败。

## 项目结构
```
practice-projects/01-knowledge-base-qa/
├── data/                  # 测试文档集
│   ├── company_policy_v1.md      # 营销类 Project X 文档
│   ├── technical_specs_v1.md     # 硬件类 Project X 文档
│   └── long_meeting_notes.md     # 长文本分块测试文档
├── chroma_db/             # 本地向量数据库存储
├── ingestion.py           # 文档解析 + 语义切分 + 索引构建
├── query_engine.py        # 基础检索 with ChromaDB 逻辑
├── evaluate.py            # 端到端效果评测（对接项目 00）
├── chromadb_guide.md      # 重点：ChromaDB 使用指南
└── requirements.txt       # 依赖声明
```

## 学习资源
- [ChromaDB 使用指南](./chromadb_guide.md)：详细介绍了向量数据库在本项目中的集成方式和核心配置。

## 技术栈与坑位说明

### 1. 填坑 A3：分块策略 (Ingestion)
在 `ingestion.py` 中，我们使用了 `SentenceSplitter`。
- **方案**：设置 `chunk_size=512` 和 `chunk_overlap=50`，并在句子边界进行切分。
- **目的**：避免将一个完整的语义块（如数据库密码）从中截断。

### 2. 本地 Embedding (技术选型)
为了解决 API 认证和中文理解问题：
- **模型**：`BAAI/bge-small-zh-v1.5`（本地运行，无需 Key）。
- **库**：`llama-index-embeddings-huggingface`。

### 3. 对接 DeepSeek (LLM)
在 `setup_settings` 中配置 `OpenAILike` 接入 DeepSeek，用于最终的回答生成。

## 坑位地图与当前进度
| 编号 | 坑 | 现象 | 根因 | 方案 | 状态 |
|------|-----|------|------|------|------|
| A1 | 语义混淆 | 问硬件 Project X 答成营销 Project X | 向量检索余弦相似度极高 | 已引入 Rerank (待调优) | 🔄 |
| A3 | 切分策略 | 无法检索到长文档深处的密码 | 分块边缘截断 | 已使用 SentenceSplitter | ✅ |
| A4 | 质量评估 | 无法量化 RAG 表现 | 缺乏度量基准 | 已对接项目 00 评估流 | ✅ |

### 📅 2026-05-09 实验记录：Reranker 悖论
在引入 `BAAI/bge-reranker-base` 后，Case 1（语义混淆）依然失败。
- **发现**：即便重排序模型加载成功，但由于初次检索（Top-K）设置太小（k=5），营销类文档未能进入候选集。
- **结论**：Reranker 的前提是“召回包含正确答案”。接下来的优化方向应转向提高 Top-K 采样宽度或优化 Query 增强。

## 运行方式
1. 确保 `.env` 配置了 DeepSeek 的 Key。
2. 构建索引：`python ingestion.py`
3. 运行评测：`python evaluate.py`
