# dataset.py
# 构造用于测试 RAG 检索精度的“语义混淆”数据集

DOCUMENTS = [
    # 类别 A: 苹果 (科技 vs 水果 vs 科学)
    {
        "id": "A1",
        "content": "苹果公司（Apple Inc.）在 2024 年秋季发布会上展示了搭载最新 A18 芯片的 iPhone 16，其 AI 处理能力大幅提升。",
        "metadata": {"category": "technology", "topic": "Apple iPhone"}
    },
    {
        "id": "A2",
        "content": "制作传统苹果派的关键在于选择口感酸甜适中的苹果，并加入少许肉桂粉提升香气。",
        "metadata": {"category": "food", "topic": "Apple Pie"}
    },
    {
        "id": "A3",
        "content": "苹果树的炭疽病是一种常见的真菌性病害，会导致果实表面出现褐色凹陷斑点，严重影响产量。",
        "metadata": {"category": "agriculture", "topic": "Apple Tree Disease"}
    },
    {
        "id": "A4",
        "content": "牛顿通过观察苹果从树上掉落，思考出了万有引力定律，这成为了现代物理学的基石之一。",
        "metadata": {"category": "science_history", "topic": "Newton's Apple"}
    },

    # 类别 B: 糖尿病 (1型 vs 2型)
    {
        "id": "B1",
        "content": "1型糖尿病是一种自身免疫性疾病，患者的免疫系统错误地攻击并破坏胰腺中产生胰岛素的细胞，导致胰岛素绝对缺乏。",
        "metadata": {"category": "medical", "topic": "Type 1 Diabetes"}
    },
    {
        "id": "B2",
        "content": "2型糖尿病是最常见的糖尿病类型，主要由身体对胰岛素产生抵抗（胰岛素抵抗）或胰岛素分泌相对不足引起，通常与肥胖和缺乏运动有关。",
        "metadata": {"category": "medical", "topic": "Type 2 Diabetes"}
    },

    # 类别 C: 法律 vs 编程 (Python)
    {
        "id": "C1",
        "content": "Python 是一种流行的高级编程语言，以其简洁的语法和强大的库生态系统（如 NumPy 和 Pandas）而闻名。",
        "metadata": {"category": "programming", "topic": "Python Language"}
    },
    {
        "id": "C2",
        "content": "在法律术语中，'Python' 有时被用作某些特定法案或监管框架的代号，特别是在处理网络安全犯罪的闭门讨论中。",
        "metadata": {"category": "legal", "topic": "Legal Codename"}
    },

    # 类别 D: 地理 (华盛顿)
    {
        "id": "D1",
        "content": "华盛顿哥伦比亚特区（Washington, D.C.）是美国的首都，坐落于波多马克河畔，不属于任何一个州。",
        "metadata": {"category": "geography", "topic": "Washington D.C."}
    },
    {
        "id": "D2",
        "content": "华盛顿州（Washington State）位于美国西北部，首府是奥林匹亚，最大的城市是西雅图，以雨林和高科技工业著称。",
        "metadata": {"category": "geography", "topic": "Washington State"}
    }
]

# 测试用例：提问 -> 期望的正确文档 ID
TEST_QUERIES = [
    {
        "query": "苹果最近发布的手机有什么特点？",
        "expected_id": "A1",
        "difficulty": "low",
        "reason": "包含明确的关键词'手机'"
    },
    {
        "query": "苹果生病了该怎么治？",
        "expected_id": "A3",
        "difficulty": "high",
        "reason": "语义混淆：'生病'可能被误解为人体疾病或电脑故障，实际指向农业病害"
    },
    {
        "query": "自身免疫系统攻击导致的血糖问题是怎么回事？",
        "expected_id": "B1",
        "difficulty": "high",
        "reason": "语义匹配：用户没有提到'1型'，需要模型理解'自身免疫'的病理特征"
    },
    {
        "query": "我想去美国首都旅游，该去哪里？",
        "expected_id": "D1",
        "difficulty": "medium",
        "reason": "需要常识关联：首都 = 华盛顿 D.C."
    },
    {
        "query": "这个编程语言的名字在法律里有什么特殊含义吗？",
        "expected_id": "C2",
        "difficulty": "high",
        "reason": "语义桥接：'这个编程语言'（指Python）与法律含义的结合"
    },
    {
        "query": "写一段关于苹果掉下来发现引力的故事。",
        "expected_id": "A4",
        "difficulty": "medium",
        "reason": "跨学科联想：苹果 + 引力"
    }
]

# ── 多跳推理测试用例（需要跨文档连接信息才能回答） ──
# 与 TEST_QUERIES 不同，每条查询期望命中多个文档的联合信息。
MULTI_HOP_QUERIES = [
    # ── 跨 Apple 系列 ──
    {
        "query": "从苹果公司推出AI手机到牛顿发现引力，'苹果'这个符号在历史上经历了怎样的演变？",
        "expected_ids": ["A1", "A4"],
        "difficulty": "multi-hop",
        "reason": "需要连接科技产品和科学史两个时代的文档"
    },
    {
        "query": "苹果树的病害和苹果派的做法有什么联系和区别？",
        "expected_ids": ["A3", "A2"],
        "difficulty": "multi-hop",
        "reason": "需要从农业病害和烹饪美食两个角度对比同一事物"
    },

    # ── 糖尿病系列 ──
    {
        "query": "1型糖尿病和2型糖尿病在病因上有什么本质区别？为什么治疗方案不同？",
        "expected_ids": ["B1", "B2"],
        "difficulty": "multi-hop",
        "reason": "需要对比两篇医学文档的病理机制并推导治疗逻辑"
    },
    {
        "query": "自身免疫攻击和胰岛素抵抗分别对应哪种糖尿病？",
        "expected_ids": ["B1", "B2"],
        "difficulty": "multi-hop",
        "reason": "需要将症状描述反向映射到正确的疾病类型"
    },

    # ── Python 系列 ──
    {
        "query": "Python 在编程语言和法律术语中分别代表什么？两种含义差别很大，请分别说明。",
        "expected_ids": ["C1", "C2"],
        "difficulty": "multi-hop",
        "reason": "同一词汇在技术和法律领域的语义对比"
    },

    # ── 华盛顿系列 ──
    {
        "query": "美国有两个华盛顿，它们的地理位置和政治身份有什么不同？",
        "expected_ids": ["D1", "D2"],
        "difficulty": "multi-hop",
        "reason": "需要区分华盛顿特区和华盛顿州两个实体"
    },

    # ── 跨类别综合 ──
    {
        "query": "苹果树的病害和iPhone新品的发布，这两个话题中的'苹果'分别指什么？",
        "expected_ids": ["A3", "A1"],
        "difficulty": "multi-hop",
        "reason": "跨语义范畴对比：农业病害 vs 科技产品"
    },
    {
        "query": "糖尿病的两种主要类型在发病机制和对胰岛素的依赖程度上有何不同？",
        "expected_ids": ["B1", "B2"],
        "difficulty": "multi-hop",
        "reason": "需要全面对比两篇糖尿病文档的病理和治疗特征"
    },
]

ALL_QUERIES = TEST_QUERIES + [
    {**q, "expected_id": q["expected_ids"][0]}  # 兼容旧字段，取第一个作为主期望
    for q in MULTI_HOP_QUERIES
]

if __name__ == "__main__":
    print(f"Dataset loaded: {len(DOCUMENTS)} documents, {len(TEST_QUERIES)} single-hop + {len(MULTI_HOP_QUERIES)} multi-hop = {len(ALL_QUERIES)} total queries.")
