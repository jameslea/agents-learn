import time
import logging
import sys
import os

# 立即配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("evaluate")

logger.info("正在启动 [评估程序]，准备加载系统模块...")
start_import_time = time.time()

# 将项目根目录和评估底座 (00-evaluation-infra) 路径加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../00-evaluation-infra")))

# pyrefly: ignore [missing-import]
from eval_framework.llm_judge import LLMJudge
from query_engine import get_query_engine

# 计算导入耗时
import_duration = time.time() - start_import_time
logger.info(f"[评估程序] 模块加载完成，耗时: {import_duration:.2f} 秒")

"""
主要组件说明：
- LLMJudge: 自定义的评估类（位于 00-evaluation-infra），利用 LLM 作为“裁判”进行评分。
- get_query_engine: 项目自定义函数，用于初始化并获取 RAG 查询引擎。
"""

def run_evaluation():
    """
    运行 RAG 系统评估流程，包含基础匹配和 LLM 评估。
    """
    judge = LLMJudge()
    engine = get_query_engine()
    
    # 定义测试用例
    # 每个案例针对一个特定的痛点 (Pitfall)
    test_cases = [
        {
            "query": "Project X 的核心指标是什么？",
            "expected_contains": "1000 万", # 营销项目中的指标
            "category": "语义混淆 (营销 vs 硬件)"
        },
        {
            "query": "Project X 硬件的安全特性是什么？",
            "expected_contains": "AES-256", # 硬件项目中的指标
            "category": "语义混淆 (营销 vs 硬件)"
        },
        {
            "query": "临时数据库的访问密码是什么？",
            "expected_contains": "ComplexPass!2025_Secret",
            "category": "长文档分块 (A3)"
        }
    ]
    
    print("开始评估...\n")
    for case in test_cases:
        print(f"[{case['category']}]")
        print(f"问题: {case['query']}")
        
        # 1. 执行 RAG 查询
        response = engine.query(case['query'])
        answer = str(response)
        
        # 获取检索到的上下文原文，用于 LLM 评估忠实度
        context = "\n".join([n.text for n in response.source_nodes])
        
        # 调试：打印检索到的源文件
        sources = [n.metadata.get('file_name', 'Unknown') for n in response.source_nodes]
        print(f"检索来源: {sources}")
        
        # 2. 基础匹配检查 (Exact Match / Contains)
        is_hit = case['expected_contains'] in answer
        
        # 3. LLM 自动化评估 (LLM-as-a-Judge)
        # 忠实度 (Faithfulness): 回答是否完全基于上下文 (拒绝幻觉)
        faithfulness = judge.evaluate_faithfulness(context, answer)
        # 相关性 (Relevance): 回答是否真正解决了用户的问题
        relevance = judge.evaluate_relevance(case['query'], answer)
        
        # 4. 输出评估结果
        print(f"回答: {answer}")
        print(f"基础命中: {'✅' if is_hit else '❌'}")
        print(f"忠实度 (Faithfulness): {faithfulness.score} ({faithfulness.reasoning})")
        print(f"相关性 (Relevance): {relevance.score} ({relevance.reasoning})")
        print("-" * 30)

if __name__ == "__main__":
    logger.info("=== 知识库评估程序启动 ===")
    run_evaluation()
    logger.info("=== 知识库评估程序运行结束 ===")
