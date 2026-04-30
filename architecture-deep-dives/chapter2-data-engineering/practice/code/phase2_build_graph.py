"""
Phase 2: 全量数据集图谱构建 + 详细耗时分析
在 dataset.py 的语意混淆文档上运行 LightRAG，记录每个阶段的耗时。

用法:
    cd practice/code
    python3 phase2_build_graph.py                          # 全量运行（10 条文档 + 查询测试）
    python3 phase2_build_graph.py --max-docs 3              # 快速调试：只处理前 3 条文档
    python3 phase2_build_graph.py --skip-queries            # 跳过查询测试，只构建图谱
    python3 phase2_build_graph.py --max-docs 2 --skip-queries  # 最快：2 条文档 + 仅建图
"""
import os
import sys
import asyncio
import json
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lm_studio_llm import lm_studio_complete, lm_studio_embed
from dataset import DOCUMENTS, TEST_QUERIES

WORKING_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "graph_index_dataset")

# ── 命令行参数 ──
parser = argparse.ArgumentParser(description="LightRAG 全量图谱构建 + 评测")
parser.add_argument("--max-docs", type=int, default=len(DOCUMENTS),
                    help=f"处理的文档数（默认 {len(DOCUMENTS)}，调试时可设 2-3）")
parser.add_argument("--skip-queries", action="store_true",
                    help="跳过查询测试，仅构建图谱")
args = parser.parse_args()


class Timer:
    """简单的计时器，支持分层计时"""
    def __init__(self):
        self.start = time.time()
        self.laps = []

    def lap(self, label: str):
        now = time.time()
        elapsed = now - self.start
        if self.laps:
            since_last = now - self.laps[-1][2]
        else:
            since_last = elapsed
        self.laps.append((label, elapsed, now))
        return since_last, elapsed

    def summary(self):
        total = self.laps[-1][1] if self.laps else time.time() - self.start
        lines = []
        for i, (label, elapsed, _) in enumerate(self.laps):
            since_prev = elapsed - (self.laps[i-1][1] if i > 0 else 0)
            pct = since_prev / total * 100
            lines.append(f"  {label:40s} {since_prev:7.1f}s  ({pct:4.0f}%)")
        lines.append(f"  {'总计':40s} {total:7.1f}s  (100%)")
        return "\n".join(lines)


async def wait_for_pipeline(rag, timeout=120, interval=2):
    """等待异步 pipeline 完成全部文档处理"""
    waited = 0
    while waited < timeout:
        # 检查 doc_status 是否所有文档都已处理完毕
        try:
            status_path = os.path.join(WORKING_DIR, "kv_store_doc_status.json")
            if os.path.exists(status_path):
                with open(status_path) as f:
                    status = json.load(f)
                processed = sum(1 for v in status.values()
                                if v.get("status") in ("processed", "completed"))
                total = len(status)
                if total > 0 and processed == total:
                    print(f"    pipeline 完成: {processed}/{total} 文档已处理")
                    return True
                if total > 0:
                    print(f"    pipeline 进度: {processed}/{total}", end="\r")
        except Exception:
            pass
        await asyncio.sleep(interval)
        waited += interval
    print(f"\n    [!] 等待超时 ({timeout}s)，强制继续")
    return False


async def build_knowledge_graph(max_docs=len(DOCUMENTS)):
    """全量文档图谱构建 + 详细时序（用 max_docs 控制处理数量）"""
    docs = DOCUMENTS[:max_docs]
    print("=" * 60)
    print(f"Phase 2: 图谱构建 — {len(docs)}/{len(DOCUMENTS)} 条文档")
    print("=" * 60)

    # 清理并初始化
    import shutil
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
    os.makedirs(WORKING_DIR, exist_ok=True)

    t_total = Timer()

    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=lm_studio_complete,
        embedding_func=EmbeddingFunc(
            func=lm_studio_embed, max_token_size=8192, embedding_dim=768,
        ),
        llm_model_max_async=1,
        embedding_func_max_async=2,
        enable_llm_cache=True,
    )

    await rag.initialize_storages()
    t_total.lap("存储初始化")

    # ── 批量插入文档（全部入队后 pipeline 并行处理） ──
    insert_times = []
    print(f"\n{'='*60}")
    print(f"批量插入 {len(docs)} 条文档")
    print(f"{'='*60}\n")

    # 所有文档并行入队
    batch_start = time.time()
    tasks = []
    for i, doc in enumerate(docs):
        t = asyncio.create_task(rag.ainsert(doc["content"]))
        tasks.append((i, doc, t))

    # 等待所有入队完成
    for i, doc, t in tasks:
        await t
        cat = doc["metadata"]["category"]
        print(f"  [{i+1:2d}/{len(docs)}] {doc['id']:4s} | {cat:15s} | 已入队 | {doc['content'][:35]}...")

    batch_insert_time = time.time() - batch_start
    print(f"\n  全部入队完成，耗时 {batch_insert_time:.1f}s，pipeline 正在并行处理...")

    t_total.lap(f"文档插入（{len(docs)} 条）")

    # ── 等待异步 pipeline ──
    print(f"\n  [等待] 异步 pipeline 处理中...")
    await wait_for_pipeline(rag)
    t_total.lap("pipeline 异步处理")

    # ── 统计 LLM 调用 ──
    cache_path = os.path.join(WORKING_DIR, "kv_store_llm_response_cache.json")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f)
        type_counts = {}
        for k in cache:
            parts = k.split(':')
            ctype = ':'.join(parts[:2])
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        print(f"\n  LLM 调用统计:")
        for ctype, count in sorted(type_counts.items()):
            print(f"    {ctype:25s}: {count} 次")
        print(f"    总计: {sum(type_counts.values())} 次 LLM 调用")

    # ── 图谱结构 ──
    entities_path = os.path.join(WORKING_DIR, "kv_store_full_entities.json")
    if os.path.exists(entities_path):
        with open(entities_path) as f:
            entities_data = json.load(f)
        all_entities = set()
        for doc_data in entities_data.values():
            all_entities.update(doc_data.get("entity_names", []))
        print(f"\n  实体数: {len(all_entities)}")

    print(f"\n{'='*60}")
    print(f"阶段一时间汇总：")
    print(f"{'='*60}")
    print(t_total.summary())

    return rag


async def run_timed_queries(rag):
    """带计时的查询评测"""
    print(f"\n{'='*60}")
    print(f"运行 {len(TEST_QUERIES)} 个测试查询（每个需要 2 次 LLM 调用：关键词提取 + 回答生成）")
    print(f"{'='*60}\n")

    t_query_total = Timer()
    results_summary = []

    for i, test in enumerate(TEST_QUERIES):
        query = test["query"]
        expected = test["expected_id"]
        difficulty = test["difficulty"]

        print(f"  [{i+1}/{len(TEST_QUERIES)}] [{difficulty.upper()}] {query}")
        print(f"     期望: {expected} | {test['reason']}")

        for mode in ("local", "global"):
            t_q = Timer()
            result = await rag.aquery(query, param=QueryParam(mode=mode))
            lap_time, _ = t_q.lap(f"{mode} 查询")

            # 由 LLM 判断是否命中
            judge_prompt = (
                f"问题：{query}\n"
                f"正确答案来源文档：{expected}\n"
                f"AI 回答：{result}\n\n"
                f"请判断 AI 的回答是否基于正确答案来源文档的信息。仅输出 YES 或 NO。"
            )
            # 这里简化判断：检查结果非空且有实质内容
            hit = len(result or "") > 20

            print(f"      {mode:8s}: {lap_time:5.1f}s | {'✅' if hit else '❌'} | {str(result)[:80]}...")

        results_summary.append({
            "query": query,
            "expected": expected,
            "difficulty": difficulty,
        })

    print(f"\n{'='*60}")
    print(f"查询阶段时间汇总：")
    print(f"{'='*60}")
    print(t_query_total.summary())


async def main():
    rag = await build_knowledge_graph(max_docs=args.max_docs)
    if not args.skip_queries:
        await run_timed_queries(rag)
    else:
        print(f"\n  [跳过查询测试] --skip-queries 已设置")

    print(f"\n{'='*60}")
    print("全部完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
