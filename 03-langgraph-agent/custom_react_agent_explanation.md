# 深入理解 LangGraph 底层手动构建 ReAct 架构

这是一个非常清晰且典型的 LangGraph **底层手动构建 ReAct (Reasoning + Acting) 架构**的代码示例 (`custom_react_agent.py`)。与“开箱即用”的封装工具（如 `create_react_agent`）不同，这段代码通过状态机（StateGraph）的形式**从零定义和组装了整个 Agent 的运行逻辑**。

以下是分模块对核心原理的详细讲解：

## 1. 核心状态的定义 (状态机的数据载体)
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
```
- **这是什么：** 定义了在整个图（Graph）各个节点之间流转的唯一数据对象，可以把它想象成在工厂流水线上流转的“账本”。
- **精髓点：** `Annotated[..., operator.add]` 是极其重要的一环。在 LangGraph 中，当一个节点处理完数据返回 `{"messages": [new_message]}` 时，如果不用 `operator.add`，旧的历史记录会被新记录**强行覆盖**。加上了 `operator.add` 这个 reducer，LangGraph 就知道自动把新产生的内容**追加（Append）** 到原有的 `messages` 列表末尾。这样大模型就能记住长篇的历史对话了。

## 2. 工具和大脑的准备
```python
@tool
def get_current_weather(location: str) -> str:
    # ...

tools = [get_current_weather]
llm = ChatOpenAI(model=model_name, temperature=0).bind_tools(tools)
```
这里为系统准备了可执行的方法，并通过 `.bind_tools(tools)` 明确告知语言模型（LLM）：“除了聊天，你现在装备了这些特定武器。当你认为需要时，可以输出标准的 JSON 格式调用它们”。这是 Tool Calling 的核心准备工作。

## 3. 三大核心运转部件（Nodes & Router）
这是这套 Agent 的灵魂所在，包含两个实体处理节点（工厂车间）和一个中枢路由器（导调中心）。

### ▶ 节点 A：推理中枢节点 (`agent_node`)
```python
def agent_node(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
```
- 这个节点的作用单纯且专一：读取当前账本（过去所有的聊天记录含工具结果），让 LLM 进行一次思考并写下输出。
- LLM 返回的内容可能是直接回复用户的内容（结束任务），也可能是一个带有 `tool_calls` 的意图对象（申请调用工具）。它不负责执行工具，只负责“想”。

### ▶ 节点 B：工具执行节点 (`tool_node`)
```python
tool_node = ToolNode(tools)
```
这其实是一个 LangGraph 内置定义好的“动作车间”。当 LLM 要求运行 `get_current_weather` 时，数据会流入这里。它负责把传入的参数取出来，真正去调用对应的 Python 函数，然后把运行的结果包装成 `ToolMessage` 发送出去。

### ▶ 调度的枢纽：条件路由函数 (`should_continue`)
```python
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
         return RouteCondition.CONTINUE
    else:
         return RouteCondition.END
```
这就是通常意义上的“海关守卫的 if-else”，它是负责指挥交通的。每次 `agent_node` 做完决定后都会问一下这个守卫：
- 如果 LLM 说要用工具（存在 `tool_calls`） -> 守卫指示去 Tools 节点；
- 如果 LLM 给了常规文字对话 -> 守卫说任务办完了，可以指向 `END` 退出系统。

## 4. 蓝图组装与编译 (StateGraph)
```python
builder = StateGraph(AgentState)
builder.add_node(NodeName.AGENT, agent_node)
builder.add_node(NodeName.TOOLS, tool_node)

builder.set_entry_point(NodeName.AGENT) 
builder.add_conditional_edges(
    NodeName.AGENT, 
    should_continue, # 判断函数
    { RouteCondition.CONTINUE: NodeName.TOOLS, RouteCondition.END: END }
)
builder.add_edge(NodeName.TOOLS, NodeName.AGENT)
```
像画状态机流程图一样：
1. `set_entry_point`: 规定一旦系统启动，第一个收到的请求一定得先进入 `agent_node` 给大脑处理。
2. `add_conditional_edges`: `agent_node` 结束后，会调用条件判断函数，可能走向工具，可能走到末尾（END）。
3. `add_edge`: **（关键闭环！）**如果去了工具节点 (`TOOLS`)，执行完之后**必须强行回退给大脑 (`AGENT`)**。因为工具只返回客观数据（比如气温 8°C），只有再交回给大脑，大脑才能结合天气写出人性化的建议。

## 5. 流式执行与状态追踪
```python
graph = builder.compile()

initial_state = {"messages": [HumanMessage(content="北京最近天气怎么样？...")]}
for event in graph.stream(initial_state):
    pass
```
- `compile()` 是将定义好的动态蓝图静态锁定为一个可真正跑起来的应用实例。
- 通过 `.stream(initial_state)`，可以在此处监控到每次数据在每个节点中流转的瞬间（比如先到 agent，再到 tools，再回 agent）。

---

## 总结
这段代码就是一个典型的 **ReAct (Reasoning and Acting) 循环**实现。它揭去了 Langchain 高级 API 层层封装的外衣，极其生动地展示了 LLM 处理复杂任务的本质机制：

> **思考(llm) -> 决定用工具 -> 路由守卫放行工具 -> 运行工具获得数据包 -> 把数据包带回给大脑再次思考 -> 大脑发现信息补全了，给出人类回答 -> 路由守卫发现无需工具了，判定图循环结束。**

---

## 进阶 1：深究 `graph.stream` 的运行机制

在代码尾部，我们使用了以下代码来驱动系统：
```python
for event in graph.stream(initial_state):
    pass
```

### 1. LangGraph 的 `stream` 究竟在流式输出什么？
在普通的 LangChain 调用中，`stream` 往往是一字一句（Token 级别）地输出文本。但在 **LangGraph** 中，`graph.stream(...)` 输出的是**“节点执行事件（Node Events）”**。每当一个节点处理完工作并输出新的状态更新时，`stream` 就会吐出一个 `event`。

### 2. `event` 里面到底装了什么？
每一次循环拿到的 `event` 都是一个字典：`{ "执行完的节点名称": { "刚才更新的状态内容" } }`。
例如：
- **第一次流转：** `agent_node` 决定调用工具 -> `{"agent": {"messages": [AIMessage(tool_calls=[...])]}}`
- **第二次流转：** `tool_node` 查到天气 -> `{"tools": {"messages": [ToolMessage(content="8°C")]}}`
- **第三次流转：** 回到 `agent_node` 得出最终结论 -> `{"agent": {"messages": [AIMessage(content="天气冷，带毛衣")]}}`

### 3. 为什么循环体里要写 `pass`？
1. **内部已接管日志：** 节点和路由函数的内部已经配置了 `logger.info(...)` 打印运行状态，如果在外层重复 `print(event)` 会导致控制台极其混乱。
2. **作为引擎的“驱动器”：** Python 的生成器必须被迭代才会往下走。这里的 `for` 循环就像履带车的发动机，拉着节点一步步前行，直到碰到 `END` 节点自然终止。这也是保留扩展性的好习惯（未来方便调试）。

---

## 进阶 2：当场景变复杂时，如何避免面条代码？

当业务场景从“查天气”演变成“编写代码、运行测试、报错分析、修改代码”的长链路时，如果在一个大图里塞几十个节点和无数的 `if-else` 条件路由，系统将面临崩溃。LangGraph 提供了以下核心拆解方案：

### 1. 多智能体架构 (Multi-Agent - Supervisor 模式) —— 最主流方案
**“分而治之，不再打造全能的上帝节点”**
如果单一 Agent 拥有太多工具，极易产生幻觉瞎调用。
- **解决方案：** 建立多个只专注一件事的小 Agent（比如专门的 `Coder`，专门的 `Researcher`），同时引入一个无工具的 **Supervisor (包工头/调度员)** 节点。
- **运作流：** User -> Supervisor -> Researcher -> Supervisor -> Coder -> Supervisor -> End。逻辑极其清晰。

### 2. 子图嵌套 (Subgraphs)
**“像搭俄罗斯套娃一样组装 StateGraph”**
一个编译好的图可以直接作为另一个大图里面的“普通节点”来用。你可以把复杂的流水线打包成子图单独维护（比如 `data_clean_graph`），在主图中只需像挂载黑盒节点一样 `builder.add_node("DataCleaner", data_clean_graph)` 即可大幅降低主业务心智负担。

### 3. 主动导航返回命令 (`Command`)
**“替代复杂的字典映射条件面条路由”**
当分支走向极其复杂时，`add_conditional_edges` 配上巨大的 mapping 字典很容易出错。新版机制允许你直接在 Node 内部决定图的走向：
```python
def agent_node(state):
    # 直接通过 Command 指定下一站去哪！
    return Command(goto="research_node", update={"messages": [response]})
```
这把“路由权”下放给了节点本身，免除外挂条件路由的繁琐。

*(注：掌握以上前三条，已经足以解决 95% 复杂系统的架构问题！在极端大型架构中还可以考虑使用**状态域隔离 (State Filtering)** 限制节点对全局状态 `AgentState` 的读写权限来防止数据污染。)*
