# 项目 00：评估与安全基础设施 (Evaluation Infra)

## 场景描述
作为横向基础设施，为所有实战项目提供自动化的质量评估（LLM-as-a-Judge）和安全防护能力。

## 项目结构
```
practice-projects/00-evaluation-infra/
├── eval_framework/
│   ├── metrics.py        # 基础评估指标（准确率、命中率等）
│   └── llm_judge.py      # 基于 LLM 的高级评估（忠实度、相关性）
├── observability/        # [规划中] 可观测性集成（如 Langfuse）
├── security/             # [规划中] 安全护栏（Guardrails）
└── requirements.txt      # 依赖声明
```

## 核心代码说明

### 1. `metrics.py`
实现了基础的量化指标：
- `exact_match`: 精确匹配。
- `contains_match`: 模糊包含匹配。
- `retrieval_hit_rate`: 检索命中率计算。

### 2. `llm_judge.py`
利用 LLM 对 RAG 的输出质量进行定性评估。
- **配置自适应**：自动读取 `.env` 中的 `OPENAI_BASE_URL` 和 `MODEL_NAME`，支持 DeepSeek 等 OpenAI 兼容接口。
- **评估维度**：
    - `evaluate_faithfulness`: 忠实度评估（回答是否基于上下文，而非幻觉）。
    - `evaluate_relevance`: 相关性评估（回答是否解决了用户问题）。
- **结构化输出**：强制返回 JSON 格式，包含分数（score）和理由（reasoning）。

## 使用方式
通常由其他项目通过 `sys.path` 引用：
```python
from eval_framework.llm_judge import LLMJudge
judge = LLMJudge()
result = judge.evaluate_faithfulness(context, answer)
```
