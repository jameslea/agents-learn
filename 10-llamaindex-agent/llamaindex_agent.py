import asyncio
import os
from pathlib import Path


STAGE_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTION = "LlamaIndex 和 LangGraph 的核心分工是什么？"


def load_env_file():
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("提示：未安装 python-dotenv，将直接读取当前 Shell 环境变量。")
        return

    load_dotenv()


def require_llamaindex_imports():
    """
    Import LlamaIndex lazily so the script can print a useful setup hint when the
    optional stage-10 dependencies have not been installed yet.
    """
    try:
        from llama_index.core import (
            MockEmbedding,
            Settings,
            SimpleDirectoryReader,
            VectorStoreIndex,
        )
        from llama_index.core.agent.workflow import FunctionAgent
        from llama_index.core.tools import QueryEngineTool
    except ImportError as exc:
        raise SystemExit(
            "缺少 LlamaIndex 依赖。请先运行：\n"
            "  pip install -r requirements.txt\n\n"
            f"原始错误: {exc}"
        ) from exc

    return {
        "MockEmbedding": MockEmbedding,
        "Settings": Settings,
        "SimpleDirectoryReader": SimpleDirectoryReader,
        "VectorStoreIndex": VectorStoreIndex,
        "FunctionAgent": FunctionAgent,
        "QueryEngineTool": QueryEngineTool,
    }


def create_llm():
    """
    Build an OpenAI-compatible LlamaIndex LLM from the same .env convention used
    by earlier stages in this repository.
    """
    model_name = os.getenv("MODEL_NAME", "deepseek-chat")
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        raise SystemExit("缺少 OPENAI_API_KEY。请先在 .env 中配置模型 API Key。")

    if api_base and "api.openai.com" not in api_base:
        try:
            from llama_index.llms.openai_like import OpenAILike
        except ImportError as exc:
            raise SystemExit(
                "当前配置了 OPENAI_BASE_URL，建议安装 OpenAI-compatible LLM 适配包：\n"
                "  pip install llama-index-llms-openai-like\n\n"
                f"原始错误: {exc}"
            ) from exc

        context_window = int(os.getenv("LLAMA_INDEX_CONTEXT_WINDOW", "32768"))
        return OpenAILike(
            model=model_name,
            api_key=api_key,
            api_base=api_base,
            is_chat_model=True,
            is_function_calling_model=True,
            context_window=context_window,
            temperature=0,
        )

    try:
        from llama_index.llms.openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "缺少 OpenAI LLM 适配包。请先运行：\n"
            "  pip install llama-index-llms-openai\n\n"
            f"原始错误: {exc}"
        ) from exc

    return OpenAI(
        model=model_name,
        api_key=api_key,
        api_base=api_base,
        temperature=0,
    )


def load_learning_documents(SimpleDirectoryReader):
    input_files = [
        STAGE_DIR / "concept.md",
        STAGE_DIR / "summary.md",
    ]
    missing_files = [path for path in input_files if not path.exists()]
    if missing_files:
        missing_list = "\n".join(f"  - {path}" for path in missing_files)
        raise SystemExit(f"缺少学习文档，无法构建索引：\n{missing_list}")

    return SimpleDirectoryReader(input_files=[str(path) for path in input_files]).load_data()


def build_query_engine(imports):
    Settings = imports["Settings"]
    MockEmbedding = imports["MockEmbedding"]
    SimpleDirectoryReader = imports["SimpleDirectoryReader"]
    VectorStoreIndex = imports["VectorStoreIndex"]

    # 使用 MockEmbedding 避免索引阶段额外调用 embedding API。这个阶段先关注
    # LlamaIndex 的数据流和 Agent 工具化路径。
    Settings.llm = create_llm()
    Settings.embed_model = MockEmbedding(embed_dim=1536)

    documents = load_learning_documents(SimpleDirectoryReader)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine(similarity_top_k=3)
    return query_engine, documents


def create_agent(imports, query_engine, documents):
    FunctionAgent = imports["FunctionAgent"]
    QueryEngineTool = imports["QueryEngineTool"]
    Settings = imports["Settings"]

    query_tool = QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="llamaindex_learning_notes",
        description=(
            "用于查询阶段 10 的 LlamaIndex 学习文档。"
            "适合回答 LlamaIndex 定位、核心概念、学习路径、"
            "以及它和 LangGraph 的对比问题。"
        ),
    )

    def list_loaded_documents() -> str:
        """列出当前 LlamaIndex 索引加载了哪些学习文档。"""
        file_names = []
        for document in documents:
            file_name = document.metadata.get("file_name", "unknown")
            if file_name not in file_names:
                file_names.append(file_name)
        return "\n".join(f"- {file_name}" for file_name in file_names)

    return FunctionAgent(
        tools=[query_tool, list_loaded_documents],
        llm=Settings.llm,
        system_prompt=(
            "你是阶段 10 的 LlamaIndex 学习助手。"
            "回答问题前，优先使用 llamaindex_learning_notes 工具查询学习文档；"
            "如果用户询问加载了哪些资料，可以使用 list_loaded_documents。"
            "回答要简洁，并明确区分 LlamaIndex 与 LangGraph 的职责。"
        ),
    )


async def main():
    load_env_file()
    imports = require_llamaindex_imports()
    query_engine, documents = build_query_engine(imports)
    agent = create_agent(imports, query_engine, documents)

    question = os.getenv("LLAMAINDEX_DEMO_QUESTION", DEFAULT_QUESTION)
    print("\n========== LlamaIndex 数据中心型 Agent ==========")
    print(f"问题: {question}\n")

    response = await agent.run(user_msg=question)
    print("========== Agent 最终回答 ==========")
    print(str(response))
    print("====================================")


if __name__ == "__main__":
    asyncio.run(main())
