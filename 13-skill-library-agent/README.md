# 阶段 13：技能库与长期学习 Agent

> 状态：✅ 已完成

本阶段研究了 Voyager 风格的技能库机制，验证了 Agent "从实践中学习"并"将经验代码化"的演进能力。理解了技能库与普通 Memory 的本质区别。

---

## 核心学习成果

- 技能的结构化定义：名称、描述、适用条件、输入/输出、实现逻辑
- 技能库工作流：任务前检索 → 任务中应用 → 任务后沉淀
- 技能库 vs 普通记忆：Memory 存"聊过什么"，技能库存"能做什么"
- 工业溯源：从 Voyager 到 Dify/Coze 平台的技能模式演进
- 详见：[concept.md](./concept.md) 与 [summary.md](./summary.md)

---

## 代码文件

| 文件 | 说明 |
|---|---|
| `skill_library_agent.py` | 基于本地 JSON 技能库的完整 Agent 实现 |
| `skills.json` | 预置技能库数据（含沉淀的新技能） |

---

## 运行示例

```bash
venv/bin/python 13-skill-library-agent/skill_library_agent.py
```

---

## 阶段总结

详见 [summary.md](./summary.md)。
