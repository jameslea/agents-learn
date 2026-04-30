import os
import json
import time
import argparse
import numpy as np
import faiss
import requests
from sentence_transformers import SentenceTransformer
from dataset import DOCUMENTS, TEST_QUERIES, MULTI_HOP_QUERIES

# 配置
EMBED_MODEL_NAME = "text-embedding-nomic-embed-text-v1.5"
LM_STUDIO_API = "http://localhost:1234/v1"
LM_STUDIO_CHAT_MODEL = "qwen/qwen3-4b-2507"
LM_STUDIO_EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"

# ── 命令行参数 ──
parser = argparse.ArgumentParser(description="向量检索模式对比评测（Baseline / Rerank / HyDE / HyDE+Rerank）")
parser.add_argument("--test-set", choices=["single", "multi", "all"], default="single",
                    help="测试集: single=语义混淆(默认), multi=多跳推理, all=两者")
parser.add_argument("--max-queries", type=int, default=8,
                    help="测试查询数（默认 8）")
parser.add_argument("--output", default="",
                    help="结果保存路径（默认不保存）")
parser.add_argument("--quick", action="store_true",
                    help="快速模式（2 条 query）")
args = parser.parse_args()

if args.quick:
    args.max_queries = min(args.max_queries, 2)
    args.test_set = "single"

if args.test_set == "single":
    QUERIES = TEST_QUERIES
elif args.test_set == "multi":
    QUERIES = MULTI_HOP_QUERIES
else:
    QUERIES = TEST_QUERIES + MULTI_HOP_QUERIES

class RAGBenchmark:
    def __init__(self):
        self.doc_contents = [doc["content"] for doc in DOCUMENTS]
        self.doc_ids = [doc["id"] for doc in DOCUMENTS]
        
        # 构建 FAISS 索引
        print("[*] 正在构建文档索引 (通过 LM Studio Embedding)...")
        # 批量获取 Embedding
        embeddings = self.get_embedding(self.doc_contents)
        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings.astype('float32'))
        print(f"[+] 索引构建完成，共 {len(self.doc_ids)} 条文档。")

    def get_embedding(self, text_or_list):
        """调用 LM Studio 生成 Embedding (支持批量)"""
        # print(f"    [API] 正在请求 LM Studio Embedding: {LM_STUDIO_EMBED_MODEL}...")
        payload = {
            "model": LM_STUDIO_EMBED_MODEL,
            "input": text_or_list
        }
        try:
            response = requests.post(f"{LM_STUDIO_API}/embeddings", json=payload, timeout=30)
            result = response.json()
            # 如果是单条文本，input 可能返回单个 embedding
            if isinstance(text_or_list, str):
                return np.array([result['data'][0]['embedding']])
            return np.array([item['embedding'] for item in result['data']])
        except Exception as e:
            print(f"    [!] Embedding 接口调用失败: {e}")
            return None

    def get_llm_rerank_score(self, query, doc_content):
        """使用 LLM 对文档进行评分 (0-10)"""
        prompt = (
            f"请判断以下文档与问题的相关性。请仅输出一个 0 到 10 之间的数字（10 表示最相关，0 表示完全无关）。\n"
            f"问题：{query}\n"
            f"文档内容：{doc_content}\n"
            f"相关性得分："
        )
        payload = {
            "model": LM_STUDIO_CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 10
        }
        try:
            response = requests.post(f"{LM_STUDIO_API}/chat/completions", json=payload, timeout=20)
            result = response.json()
            score_text = result['choices'][0]['message']['content'].strip()
            # 简单清洗，只保留数字
            import re
            score_match = re.search(r"(\d+(\.\d+)?)", score_text)
            if score_match:
                return float(score_match.group(1))
            return 0.0
        except Exception:
            return 0.0

    def get_hyde_doc(self, query):
        """HyDE: 调用 LM Studio 生成假设性文档"""
        print(f"    [API] 正在请求 LM Studio Chat: {LM_STUDIO_CHAT_MODEL} (HyDE)...")
        prompt = f"你是一个专业的搜索助手。请针对以下问题写一段详细的、事实性的回答（约100字），用于帮助搜索引擎匹配到最相关的真实文档。\n\n问题：{query}\n\n回答："
        payload = {
            "model": LM_STUDIO_CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        try:
            response = requests.post(f"{LM_STUDIO_API}/chat/completions", json=payload, timeout=60)
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"    [HyDE] 已生成假设文档 ({len(content)} 字)")
            return content
        except Exception as e:
            print(f"    [!] HyDE 接口调用失败: {e}")
            return query

    def retrieve(self, query, top_k=5):
        """基础向量检索"""
        query_vec = self.get_embedding(query)
        if query_vec is None: return []
        distances, indices = self.index.search(query_vec.astype('float32'), top_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0: continue
            results.append({
                "id": self.doc_ids[idx],
                "content": self.doc_contents[idx],
                "score": float(distances[0][i])
            })
        return results

    def run_baseline(self, query):
        """模式 1: 仅向量检索"""
        start = time.time()
        results = self.retrieve(query, top_k=3)
        return [r["id"] for r in results], time.time() - start

    def run_rerank(self, query):
        """模式 2: 向量检索 + LLM Rerank"""
        start = time.time()
        # 1. 粗排
        initial_results = self.retrieve(query, top_k=5) # 减少 LLM 开销，精排前 5 个
        
        # 2. 精排
        print(f"    [Rerank] 正在使用 {LM_STUDIO_CHAT_MODEL} 对 {len(initial_results)} 条文档进行打分...")
        scored_results = []
        for r in initial_results:
            score = self.get_llm_rerank_score(query, r["content"])
            scored_results.append((r, score))
            # print(f"      - ID: {r['id']}, LLM Score: {score}")
        
        # 3. 按分数重排
        reranked = sorted(scored_results, key=lambda x: x[1], reverse=True)
        latency = time.time() - start
        return [r[0]["id"] for r in reranked[:3]], latency

    def run_hyde(self, query):
        """模式 3: HyDE 联想检索"""
        start = time.time()
        # 1. 生成假设文档
        hyde_doc = self.get_hyde_doc(query)
        # 2. 用假设文档进行检索
        results = self.retrieve(hyde_doc, top_k=3)
        latency = time.time() - start
        return [r["id"] for r in results], latency

    def run_hyde_rerank(self, query):
        """模式 4: HyDE + LLM Rerank (组合拳)"""
        start = time.time()
        # 1. 生成假设文档
        hyde_doc = self.get_hyde_doc(query)
        # 2. 用假设文档进行粗排 (Top-10)
        initial_results = self.retrieve(hyde_doc, top_k=5)
        # 3. 使用 LLM 进行精排
        print(f"    [HyDE+Rerank] 正在对 HyDE 召回的 {len(initial_results)} 条文档进行重排...")
        scored_results = []
        for r in initial_results:
            score = self.get_llm_rerank_score(query, r["content"])
            scored_results.append((r, score))
        
        reranked = sorted(scored_results, key=lambda x: x[1], reverse=True)
        latency = time.time() - start
        return [r[0]["id"] for r in reranked[:3]], latency

def evaluate(query_set, test_set_name="single", max_queries=None, output_path=""):
    """统一评测入口，支持 single-hop 和 multi-hop 测试集"""
    queries = query_set[:max_queries]
    benchmark = RAGBenchmark()

    modes = {
        "Baseline": benchmark.run_baseline,
        "Rerank": benchmark.run_rerank,
        "HyDE": benchmark.run_hyde,
        "HyDE+Rerank": benchmark.run_hyde_rerank,
    }

    results_report = []

    print("\n" + "=" * 50)
    print(f"评测: {test_set_name} | {len(queries)} 条查询 × {len(modes)} 种模式")
    print("=" * 50)

    for test in queries:
        query = test["query"]
        # 兼容 single-hop (expected_id) 和 multi-hop (expected_ids)
        expected_ids = test.get("expected_ids")
        if expected_ids is None:
            expected_ids = [test["expected_id"]]
        expected_label = ", ".join(expected_ids)
        is_multi = len(expected_ids) > 1

        print(f"\n[测试项] 问题: {query}")
        print(f"        期望: [{expected_label}] ({test['difficulty']})")

        row = {
            "query": query,
            "expected_ids": expected_ids,
            "difficulty": test["difficulty"],
        }

        for mode_name, mode_func in modes.items():
            top_ids, latency = mode_func(query)
            # multi-hop: 所有期望文档都出现才算命中
            if is_multi:
                hit = all(eid in top_ids for eid in expected_ids)
            else:
                hit = expected_ids[0] in top_ids

            rank = next((i + 1 for i, eid in enumerate(top_ids) if eid in expected_ids), "N/A")

            status = "✓" if hit else "✗"
            print(f"  - [{mode_name:8}] 命中: {status} | 排名: {rank} | 耗时: {latency:.4f}s")

            row[f"{mode_name}_hit"] = hit
            row[f"{mode_name}_rank"] = rank
            row[f"{mode_name}_latency"] = latency

        results_report.append(row)

    # 汇总
    print("\n" + "=" * 50)
    print(f"评测汇总 — {test_set_name}")
    print("=" * 50)
    for mode in modes.keys():
        hits = sum(1 for r in results_report if r[f"{mode}_hit"])
        total = len(results_report)
        avg_latency = sum(r[f"{mode}_latency"] for r in results_report) / total
        print(f"模式: {mode:8} | 命中率: {hits}/{total} ({hits / total * 100:.1f}%) | 平均耗时: {avg_latency:.4f}s")

    # 保存结果
    if output_path:
        with open(output_path, "w") as f:
            json.dump({"test_set": test_set_name, "results": results_report}, f, ensure_ascii=False, indent=2)
        print(f"  结果已保存: {output_path}")


if __name__ == "__main__":
    evaluate(query_set=QUERIES, test_set_name=args.test_set, max_queries=args.max_queries, output_path=args.output)
