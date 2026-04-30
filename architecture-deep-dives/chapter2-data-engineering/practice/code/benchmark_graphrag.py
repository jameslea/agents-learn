"""
Phase 3: GraphRAG 检索评测集成
基于 phase2 构建的 graph_index_dataset 运行 LightRAG Local/Global 检索评测。

用法:
    cd practice/code
    python3 benchmark_graphrag.py                                     # 单跳测试集
    python3 benchmark_graphrag.py --test-set multi                    # 多跳测试集
    python3 benchmark_graphrag.py --test-set all --skip-judge         # 全量测试集，跳过 LLM 判断
    python3 benchmark_graphrag.py --quick                             # 极速模式
"""
import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lm_studio_llm import lm_studio_complete, lm_studio_embed
from dataset import DOCUMENTS, TEST_QUERIES, MULTI_HOP_QUERIES

WORKING_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "graph_index_dataset")

# ── 命令行参数 ──
parser = argparse.ArgumentParser(description="GraphRAG 检索评测")
parser.add_argument("--max-queries", type=int, default=8,
                    help="测试查询数（默认 8）")
parser.add_argument("--test-set", choices=["single", "multi", "all"], default="single",
                    help="测试集: single=语义混淆(默认), multi=多跳推理, all=两者")
parser.add_argument("--mode", choices=["local", "global", "both"], default="both")
parser.add_argument("--skip-judge", action="store_true",
                    help="跳过 LLM 判断，仅记录原始回答")
parser.add_argument("--quick", action="store_true",
                    help="极速模式（等价于 --max-queries 2 --skip-judge --test-set single）")
parser.add_argument("--working-dir", default=WORKING_DIR,
                    help="图谱数据目录（默认 graph_index_dataset）")
args = parser.parse_args()

if args.quick:
    args.max_queries = min(args.max_queries, 2)
    args.skip_judge = True
    args.test_set = "single"

# 根据 --test-set 选择查询列表
if args.test_set == "single":
    QUERIES = TEST_QUERIES
elif args.test_set == "multi":
    QUERIES = MULTI_HOP_QUERIES
else:
    QUERIES = TEST_QUERIES + MULTI_HOP_QUERIES


def build_working_dir_size(wd: str) -> str:
    """返回工作目录的概览信息"""
    if not os.path.exists(wd):
        return "不存在"
    files = os.listdir(wd)
    total_size = sum(os.path.getsize(os.path.join(wd, f)) for f in files)
    size_mb = total_size / 1024 / 1024
    return f"{len(files)} 个文件, {size_mb:.1f} MB"


async def llm_judge_multi(query: str, expected_contents: list[str], answer: str):
    """用 LM Studio 判断 GraphRAG 回答是否覆盖了全部期望文档的信息"""
    if not answer or len(answer.strip()) < 10:
        return False, "EMPTY"

    docs_text = "\n---\n".join(
        f"文档{i+1}：{c}" for i, c in enumerate(expected_contents)
    )
    prompt = (
        f"判断 AI 的回答是否涵盖了以下全部文档中的核心信息。\n\n"
        f"问题：{query}\n"
        f"参考文档：\n{docs_text}\n"
        f"AI 回答：{answer}\n\n"
        f"AI 的回答是否涵盖了以上所有文档中的关键内容？仅输出 YES 或 NO。"
    )
    try:
        verdict = await lm_studio_complete(
            prompt, system_prompt="只输出 YES 或 NO，不要输出其他内容。"
        )
        verdict = verdict.strip().upper()
        return "YES" in verdict, verdict
    except Exception as e:
        print(f"      [!] 判断调用失败: {e}")
        return None, f"ERROR: {e}"


async def main():
    print("=" * 60)
    print("Phase 3: GraphRAG 检索评测集成")
    print("=" * 60)
    print(f"  工作目录: {args.working_dir} ({build_working_dir_size(args.working_dir)})")
    print(f"  查询模式: {args.mode}")
    print(f"  测试查询: {args.max_queries} 条")
    print(f"  LLM 判断: {'跳过' if args.skip_judge else '启用'}")

    # 1. 检查图谱数据
    if not os.path.exists(args.working_dir):
        print(f"\n[!] 图谱数据不存在: {args.working_dir}")
        print(f"    请先运行 phase2_build_graph.py 构建图谱")
        sys.exit(1)

    # 2. 初始化 LightRAG（加载已有图谱，不重建）
    print(f"\n[*] 初始化 LightRAG，加载已有图谱...")
    t0 = time.time()

    rag = LightRAG(
        working_dir=args.working_dir,
        llm_model_func=lm_studio_complete,
        embedding_func=EmbeddingFunc(
            func=lm_studio_embed, max_token_size=8192, embedding_dim=768,
        ),
        llm_model_max_async=1,
        embedding_func_max_async=2,
        enable_llm_cache=True,
    )

    await rag.initialize_storages()
    print(f"  [✓] 存储加载完成 ({time.time() - t0:.1f}s)")

    # 3. 准备查询
    queries = QUERIES[:args.max_queries]
    modes = ["local", "global"] if args.mode == "both" else [args.mode]

    print(f"\n{'=' * 60}")
    print(f"测试集: {args.test_set} | {len(queries)} 条查询 × {len(modes)} 种模式")
    print(f"{'=' * 60}\n")

    # 4. 执行评测
    all_results = []

    for qi, test in enumerate(queries):
        query = test["query"]
        # 兼容 single-hop (expected_id) 和 multi-hop (expected_ids)
        expected_ids = test.get("expected_ids")
        if expected_ids is None:
            expected_ids = [test["expected_id"]]
        expected_docs = [d for d in DOCUMENTS if d["id"] in expected_ids]
        expected_contents = [d["content"] for d in expected_docs]

        expected_label = ", ".join(expected_ids)
        is_multi = len(expected_ids) > 1

        print(f"  [{qi + 1}/{len(queries)}] [{test['difficulty'].upper()}] {query}")
        print(f"     期望: [{expected_label}]")

        for mode in modes:
            t1 = time.time()
            try:
                answer = await rag.aquery(query, param=QueryParam(mode=mode))
            except Exception as e:
                answer = f"[ERROR] {e}"
            latency = time.time() - t1

            if args.skip_judge:
                hit, judge_raw = None, "SKIP"
            else:
                hit, judge_raw = await llm_judge_multi(query, expected_contents, answer)

            status = "✓" if hit is True else ("?" if hit is None else "✗")
            print(f"      {mode:8s}: {latency:6.1f}s | {status} | {str(answer)[:70]}...")

            all_results.append({
                "query": query,
                "expected_ids": expected_ids,
                "mode": mode,
                "difficulty": test["difficulty"],
                "test_set": args.test_set,
                "latency_s": round(latency, 1),
                "hit": hit,
                "judge_raw": judge_raw,
                "answer_preview": str(answer)[:120],
            })

    # 5. 汇总
    print(f"\n{'=' * 60}")
    print(f"评测汇总")
    print(f"{'=' * 60}")

    for mode in modes:
        mode_results = [r for r in all_results if r["mode"] == mode]
        hits = sum(1 for r in mode_results if r["hit"] is True)
        misses = sum(1 for r in mode_results if r["hit"] is False)
        errors = sum(1 for r in mode_results if r["hit"] is None)
        total = len(mode_results)
        avg_latency = sum(r["latency_s"] for r in mode_results) / total

        if hits + misses > 0:
            judged = hits + misses
            print(f"  {mode:8s}: 命中 {hits}/{judged} ({hits / judged * 100:.0f}%)"
                  f" | 平均 {avg_latency:.1f}s"
                  f" | 未判断 {errors}" if errors else "")
        else:
            print(f"  {mode:8s}: 平均 {avg_latency:.1f}s | 未启用判断")

    # 6. 保存结果
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "graphrag_benchmark_results.json"
    )
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
