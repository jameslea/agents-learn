# 项目 01：企业知识库问答系统 (Knowledge Base QA)

## 场景描述
针对企业内部文档（制度、方案、会议纪要）的精准问答系统。本项目重点解决 RAG（检索增强生成）中的核心痛点：
- **语义混淆**：不同项目（如 Project X）名称相同但领域不同（营销 vs 硬件）导致的检索错误。
- **长文本截断**：固定长度切分导致关键信息（如密码、技术指标）被跨块截断。
- **效果评估**：缺乏量化手段衡量 RAG 系统的准确性与性能。

## 技术栈 (Tech Stack)

| 维度 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **核心框架** | **LlamaIndex (v0.12+)** | 企业级 RAG 编排框架，负责文档加载、索引构建及查询路由。 |
| **向量数据库** | **ChromaDB** | 本地高性能向量存储，支持元数据过滤与索引持久化。 |
| **Embedding 模型** | **BAAI/bge-small-zh-v1.5** | 本地运行的中文嵌入模型，在 HuggingFace C-MTEB 榜单表现优异，检索精度高。 |
| **Reranker 模型** | **BAAI/bge-reranker-base** | Cross-Encoder 架构，对粗排结果进行二次语义打分，大幅提升 top-1 准确率。 |
| **大语言模型 (LLM)** | **DeepSeek / OpenAI / MiniMax / custom** | 通过统一 OpenAI-compatible 工厂接入，负责最终的答案合成与推理。 |
| **切分策略** | **SentenceSplitter** | 智能句子边界切分，设置 `chunk_size=512`，确保语义块的完整性。 |
| **可观测性** | **LlamaDebugHandler** | 记录并打印检索、重排、生成各环节的耗时，辅助性能优化。 |

## 项目结构
```
practice-projects/01-knowledge-base-qa/
├── data/                  # 测试文档集
│   ├── company_policy_v1.md      # 营销类 Project X 文档
│   ├── technical_specs_v1.md     # 硬件类 Project X 文档
│   └── long_meeting_notes.md     # 包含密码的长文本测试文档
├── chroma_db/             # 持久化存储目录 (自动生成)
├── ingestion.py           # 数据摄入流水线：解析 -> 语义切分 -> 索引持久化
├── query_engine.py        # 核心查询引擎：宽检索 + 严重排 + 性能监控
├── reranker.py            # 重排逻辑封装：支持模型自动下载与硬件加速检测
├── evaluate.py            # 端到端效果评测：对接 00 库进行 LLM-as-a-Judge 评估
├── chromadb_guide.md      # ChromaDB 技术专题手册
└── requirements.txt       # 项目依赖声明
```

## 核心流程说明

### 1. “宽进严出”的检索策略
本项目采用了二级过滤架构：
1. **粗排 (Retrieval)**：使用 `bge-small-zh` 向量模型，从库中检索出 Top 10 的候选片段。
2. **精排 (Reranking)**：使用 `bge-reranker-base` 对 Top 10 片段进行交叉编码打分，筛选出最相关的 Top 2。
*解决痛点：当用户问题在向量空间中与错误文档过于接近时，重排模型能识别更深层的语义差异。*

### 2. 语义完整性分块
通过 `SentenceSplitter` 实现，避免了 `TokenTextSplitter` 可能导致的文本硬截断问题。
- **配置**：`chunk_size=512`, `chunk_overlap=50`。
- **效果**：长文档中的密码（如 `ComplexPass!2025_Secret`）会被保留在同一个 Chunk 中，不会因为跨页或跨块导致检索失败。

## 坑位地图 (Pitfalls & Solutions)

| 编号 | 坑点 | 现象 | 根因 | 解决方案 | 状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A1** | 语义混淆 | 问硬件 Project X 答成营销 Project X | 向量余弦相似度区分度不足 | 引入 **Reranker** + 调大初筛 **Top-K** | ✅ |
| **A3** | 分块截断 | 无法检索到文档深处的敏感信息 | 关键信息在分块边缘被切断 | 使用 **SentenceSplitter** 保证句子完整 | ✅ |
| **A4** | 质量盲区 | 无法量化 RAG 表现 | 缺乏端到端度量基准 | 接入 **00-evaluation-infra** 自动化评分 | ✅ |

## 运行方式
1. **环境配置**：复制 `.env.example` 并填写 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY`；DeepSeek/MiniMax 可分别使用 `DEEPSEEK_API_KEY`、`MINIMAX_API_KEY`。
2. **数据处理**：运行 `python ingestion.py` 构建并持久化索引。
3. **性能测试**：运行 `python query_engine.py` 查看单次查询的各环节耗时。
4. **效果评估**：运行 `python evaluate.py` 获取系统忠实度 (Faithfulness) 与相关性 (Relevance) 评分。

## 学习资源
- [ChromaDB 使用指南](./chromadb_guide.md)：深入了解向量库配置。
- [LlamaIndex 官方文档](https://docs.llamaindex.ai/)：核心框架参考。
