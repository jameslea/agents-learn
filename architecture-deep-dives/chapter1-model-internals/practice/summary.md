# 第一章：模型底层原理 —— 实践总结

## 1. Token 效率实战
通过 `token_analysis.py` 的测试，我们观察到：
- **模型差异**：GPT-4 (tiktoken) 在处理中文时效率较低（1字符 > 1 Token），而 Qwen2.5 (transformers) 对中文有显著优化（2.3字符/Token）。
- **对 Agent 的影响**：使用中文优化模型可以有效降低费用并变相增加 Agent 的有效记忆长度。

## 2. 上下文缓存 (Prompt Caching)
- **核心原则**：**静态在前，动态在后**。
- **最佳实践**：
    - ✅ 将 `System Prompt` 和 `Tool Descriptions` 放在请求的最前端。
    - ❌ 严禁在 Prompt 开头插入 `Session ID`、`Timestamp` 或 `Random Seed`。

## 3. DPO 逻辑练习
- 我们练习了如何构建 `Chosen` vs `Rejected` 样本。
- **关键启示**：DPO 的价值不在于教模型“做什么”，而在于通过对比教模型“**不该做什么**”，这对于修复 Agent 的死循环和幻觉至关重要。

## 4. 推理与量化 (总结)
- **Mac 平台**：优先选择 **GGUF** 格式，利用统一内存。
- **生产环境 (Nvidia)**：优先选择 **AWQ + vLLM**，追求并发吞吐。
- **警告**：4-bit 量化会显著降低 JSON 遵循率，若 Agent 频繁报 JSON 解析错误，应考虑升级至 8-bit 或使用 Tool-use 专用微调模型。

---
**下一步建议**：
如果您觉得模型层面的探索已经足够，我们可以进入 **第二章：深度数据工程 (Advanced Data)**，探索如何处理复杂的 PDF、表格以及构建更强大的 GraphRAG。
