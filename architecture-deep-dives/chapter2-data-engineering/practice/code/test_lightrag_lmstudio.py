"""
Phase 1: LightRAG + LM Studio 连通性测试
验证 LightRAG 能否通过 LM Studio 的 OpenAI 兼容接口完成实体抽取和查询。

用法:
    cd practice/code
    python3 test_lightrag_lmstudio.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lm_studio_llm import lm_studio_complete, lm_studio_embed

WORKING_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "graph_index_test")


async def test_mini_graph():
    """用 3 条文档跑 LightRAG 最小闭环"""
    print("=" * 60)
    print("LightRAG + LM Studio 最小闭环测试")
    print("=" * 60)

    # 清理上次测试数据
    import shutil
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
    os.makedirs(WORKING_DIR, exist_ok=True)

    # 初始化 LightRAG — 使用 LM Studio 作为后端
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=lm_studio_complete,
        embedding_func=EmbeddingFunc(
            func=lm_studio_embed,
            max_token_size=8192,
            embedding_dim=768,
        ),
        llm_model_max_async=1,
        embedding_func_max_async=1,
        enable_llm_cache=True,
    )

    # 插入 3 条测试文档（新能源汽车领域，实体之间有交叉关系）
    test_docs = [
        "特斯拉（Tesla）是一家美国电动车制造商，由 Elon Musk 领导，总部位于得克萨斯州奥斯汀。",
        "比亚迪是中国最大的新能源汽车制造商，其刀片电池技术在业界享有盛誉。",
        "宁德时代（CATL）是全球最大的动力电池供应商，为特斯拉、宝马等车企提供电池。",
    ]

    # 初始化存储（LightRAG 1.4+ 需要）
    print("\n[1/3] 正在初始化存储...")
    await rag.initialize_storages()
    print("  存储初始化完成")

    print("\n  [正在插入] 正在插入测试文档...")
    for i, doc in enumerate(test_docs):
        await rag.ainsert(doc)
        print(f"  文档 {i+1} 插入完成 ({len(doc)} 字)")

    # 等待异步 pipeline 完成
    print("\n  [等待] 等待异步图谱构建完成...")
    await asyncio.sleep(5)

    # 检查图谱数据
    print("\n[2/3] 检查图谱存储...")
    graph_dir = WORKING_DIR
    for root, dirs, files in os.walk(graph_dir):
        level = root.replace(graph_dir, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 2 * (level + 1)
        for file in files:
            fpath = os.path.join(root, file)
            size = os.path.getsize(fpath)
            print(f"{sub_indent}{file} ({size} bytes)")

    # 查询测试
    print("\n[3/3] 查询测试...")

    print("\n  >> Local 查询: '特斯拉和哪家电池供应商有合作？'")
    result = await rag.aquery(
        "特斯拉和哪家电池供应商有合作？",
        param=QueryParam(mode="local"),
    )
    print(f"  结果: {result}")

    print("\n  >> Global 查询: '新能源汽车领域的电池供应商有哪些？'")
    result = await rag.aquery(
        "新能源汽车领域的电池供应商有哪些？",
        param=QueryParam(mode="global"),
    )
    print(f"  结果: {result}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    return rag


if __name__ == "__main__":
    asyncio.run(test_mini_graph())
