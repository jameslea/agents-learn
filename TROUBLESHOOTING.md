# Agent 开发踩坑日记 (Troubleshooting)

在本项目长达 9 个阶段的开发与探索中，我们遇到了许多由于框架迭代、模型适配及库冲突带来的真实问题。以下是我们的解决方案，希望能帮到后来的开发者。

---

## 1. CrewAI 与 Pydantic 的深度冲突 (2026-04-16)

### 问题描述
在使用 `CrewAI 1.x` 时，直接传入 LangChain 的 `ChatOpenAI` 实例会触发 Pydantic 校验错误：
`pydantic_core._pydantic_core.ValidationError`。

### 踩坑原因
最新版的 CrewAI 底层集成了 LiteLLM，它期望使用自己封装的 `LLM` 类，而不是传统的 LangChain 对象。一旦混合使用，Pydantic 无法正确序列化这两个不同版本的模型接口。

### 解决方案
改用 CrewAI 原生的 `LLM` 包装器：
```python
from crewai import LLM
llm = LLM(
    model="openai/deepseek-chat",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
```

---

## 2. smolagents API 快速更迭 (2026-04-16)

### 问题描述
许多旧教程中提到的 `LocalPythonInterpreter` 无法导入。

### 踩坑原因
`smolagents` 库更新极快（当前版本 1.x），原有的 `Interpreter` 已被重构为更系统的 `Executor` 架构。

### 解决方案
将类引用从 `LocalPythonInterpreter` 更改为 `LocalPythonExecutor`，其路径也通常位于 `smolagents.local_python_executor`。

---

## 3. AutoGen 对非 OpenAI 模型的限制

### 问题描述
使用 DeepSeek 或本地 Llama 模型连接 AutoGen 的 `OpenAIChatCompletionClient` 时，程序抛出：
`ValueError: model_info is required when model name is not a valid OpenAI model`

### 踩坑原因
AutoGen 为了优化（如计算 Token、成本），会去查一个内置的模型列表。如果你的模型不在列表里，它不知道该模型是否支持“函数调用”或“视觉”，因此强制要求你手动声明模型能力。

### 解决方案
手动传入 `ModelInfo` 对象：
```python
from autogen_core.models import ModelInfo
model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    model_info=ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family="unknown"
    )
)
```

---

## 4. LangGraph 状态丢失 (State Management)

### 问题描述
在多步循环中，发现字典里的某些 key 莫名其妙消失或未更新。

### 踩坑原因
虽然 Python 字典是灵活的，但 LangGraph 依靠 **Reducer** 函数来合并状态。如果你直接在节点里 `return new_dict`，它会尝试做合并；如果不小心拼错 key，就像是往错误的抽屉里塞东西。

### 最佳实践
**核心建议**：像本项目阶段 05 那样，使用 **Pydantic `BaseModel`** 定义状态，并配合 `Enum` 作为 key 的常量引用。
```python
class StateKey(str, Enum):
    QUESTION = "question"
    DOCUMENTS = "documents"
    # ...
```
这种做法虽然写起来繁琐，但直接消灭了 90% 的魔法字符串错误。
