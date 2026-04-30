#!/usr/bin/env python3
"""
Phase 5: 全模式对比汇总
读取各 benchmark 的结果 JSON，生成统一对比表。

用法:
    cd practice/code
    python3 phase5_comparison.py
"""
import json
import os
import sys
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ── 数据来源配置 ──
SOURCES = {
    "vector_single": "results_benchmark_single.json",
    "vector_multi": None,  # 待运行
    "graphrag": "graphrag_benchmark_results.json",
}

# GraphRAG 结果文件存储时用 test_set 字段区分
# 但之前的 quick 运行没有保存 test_set 信息，需要处理


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def extract_vector_results(data):
    """从 benchmark_rag.py 的输出 JSON 提取各模式数据"""
    if not data or "results" not in data:
        return {}
    results = {}
    for row in data["results"]:
        query = row["query"]
        results[query] = {}
        for key, val in row.items():
            for mode_prefix in ("Baseline", "Rerank", "HyDE"):
                if key.startswith(mode_prefix):
                    field = key[len(mode_prefix) + 1:]  # hit / rank / latency
                    results[query].setdefault(mode_prefix, {})[field] = val
    return results


def extract_graphrag_results(data):
    """从 benchmark_graphrag.py 的输出 JSON 提取各模式数据"""
    if not data:
        return {}
    results = {}
    for row in data:
        query = row["query"]
        results.setdefault(query, {})
        mode_label = f"GraphRAG-{row['mode'].capitalize()}"
        results[query][mode_label] = {
            "hit": row["hit"],
            "latency": row["latency_s"],
            "answer": row.get("answer_preview", ""),
        }
    return results


def build_comparison_table(vector_data, graphrag_data, title="对比表"):
    """合并两种来源的数据，生成统一表格"""
    all_queries = set()
    if vector_data:
        all_queries.update(vector_data.keys())
    if graphrag_data:
        all_queries.update(graphrag_data.keys())

    all_modes = ["Baseline", "Rerank", "HyDE", "HyDE+Rerank", "GraphRAG-Local", "GraphRAG-Global"]

    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")

    # 表头
    header = f"{'查询':30s}"
    for mode in all_modes:
        header += f" | {mode:15s}"
    print(header)
    print("-" * len(header))

    mode_stats = defaultdict(lambda: {"hits": 0, "total": 0, "latencies": []})

    for q in sorted(all_queries, key=lambda x: list(all_queries).index(x) if x in all_queries else 0):
        q_short = q if len(q) < 28 else q[:26] + ".."
        row = f"{q_short:30s}"

        for mode in all_modes:
            hit = None
            latency = None

            # 从向量结果找
            if vector_data and q in vector_data:
                if mode in vector_data[q]:
                    hit = vector_data[q][mode].get("hit")
                    latency = vector_data[q][mode].get("latency")

            # 从 GraphRAG 结果找
            if graphrag_data and q in graphrag_data:
                if mode in graphrag_data[q]:
                    hit = graphrag_data[q][mode].get("hit")
                    latency = graphrag_data[q][mode].get("latency")

            if hit is not None:
                mode_stats[mode]["total"] += 1
                if hit:
                    mode_stats[mode]["hits"] += 1
            if latency is not None:
                mode_stats[mode]["latencies"].append(float(latency))

            display = hit_to_char(hit)
            row += f" | {display:15s}"

        print(row)

    # 汇总行
    print("-" * len(header))
    summary = f"{'命中率':30s}"
    for mode in all_modes:
        s = mode_stats[mode]
        if s["total"] > 0:
            pct = s["hits"] / s["total"] * 100
            avg_lat = sum(s["latencies"]) / len(s["latencies"]) if s["latencies"] else 0
            summary += f" | {s['hits']}/{s['total']} ({pct:.0f}%) {avg_lat:.1f}s".ljust(15)[:15]
        else:
            summary += f" | {'N/A':15s}"
    print(summary)

    print(f"{'=' * 80}\n")

    return mode_stats


def hit_to_char(hit):
    if hit is True:
        return "✓"
    elif hit is False:
        return "✗"
    else:
        return "?"


def main():
    # 加载数据
    vector_single = load_json(os.path.join(DATA_DIR, SOURCES["vector_single"]))
    vector_multi_path = SOURCES["vector_multi"]
    vector_multi = load_json(os.path.join(DATA_DIR, vector_multi_path)) if vector_multi_path and os.path.exists(os.path.join(DATA_DIR, vector_multi_path)) else None
    graphrag_data = load_json(os.path.join(DATA_DIR, SOURCES["graphrag"]))

    # 按 test_set 分组 GraphRAG 结果
    graphrag_by_set = defaultdict(list)
    graphrag_all = defaultdict(list)
    if graphrag_data:
        for row in graphrag_data:
            ts = row.get("test_set", "unknown")
            graphrag_by_set[ts].append(row)

    # 提取向量结果（单跳 test_set）
    vec_single = extract_vector_results(vector_single)
    vec_multi = extract_vector_results(vector_multi)

    # 按 test_set 提取 GraphRAG 结果
    def extract_grr(rows):
        return extract_graphrag_results(rows)

    gr_single = extract_grr(graphrag_by_set.get("single", []))
    gr_multi = extract_grr(graphrag_by_set.get("multi", []))

    # 输出对比表
    print("\n" + "#" * 80)

    # 单跳对比
    has_single = bool(vec_single) or bool(gr_single)
    has_multi = bool(vec_multi) or bool(gr_multi)

    if has_single:
        build_comparison_table(vec_single, gr_single, "语义混淆测试集 (Single-Hop)")
    if has_multi:
        build_comparison_table(vec_multi, gr_multi, "多跳推理测试集 (Multi-Hop)")
    if not has_single and not has_multi:
        print("没有找到任何结果数据。请先运行 benchmark 脚本。")
        print("  cd practice/code")
        print("  python3 benchmark_rag.py --test-set single --output ../data/results_benchmark_single.json")
        print("  python3 benchmark_rag.py --test-set multi --output ../data/results_benchmark_multi.json")
        print("  python3 benchmark_graphrag.py --test-set all --skip-judge")


if __name__ == "__main__":
    main()
