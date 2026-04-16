# 多智能体 Supervisor 模式架构解析

这份 `multi_agent_supervisor.py` 的代码极其经典，它展示了工业界目前处理复杂任务的标配做法：**Hub-and-Spoke（星型拓扑）的多智能体协作模式**。

如果说单智能体 `custom_react_agent` 像是一个手忙脚乱的“全栈程序员帮办”；这里就是一家正规的公司：有专门的 **老板(Supervisor)**、**研究员(Researcher)** 和 **分析师(Analyst)**，大家职责分离，层层协同。

我们来看看它是如何组装起来的：

### 1. 状态账本的扩展 (`AgentState`)
```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next: str            # 指定下一个接手的工种名称
    last_speaker: str    # 记录上一步是谁干的活
```
与之前只有 `messages` 相比，多智能体最核心的标志就是增加了**流转控制字段**。
- `next`：是老板（Supervisor）用来填写的信封，写着“下一站发往哪里”。
- `last_speaker`：这是我们在代码底层留的神奇字段，专门用来**防内卷和防死循环**。

### 2. 定义打工人（Worker Nodes）
大家各司其职，没有哪一个是全能的：

**1号员工：Researcher (研究员)**
```python
researcher_agent = create_agent(..., tools=[wikipedia_tool], ...)
```
它本身是一个独立的小 Agent，**拥有查维基百科的特权**。遇到不懂的历史它会去搜，甚至搜不到还会换个词继续搜。

**2号员工：Analyst (分析师)**
```python
analyst_agent = analyst_prompt | llm
```
这甚至不算传统意义的 Agent，连工具都不给配。它是一段纯粹的文本处理链条（LCEL），它唯一的作用就是：戴着“高级分析师”的帽子，将之前所有收集到的乱七八糟信息，用最优美的文字归纳总结出来。

### 3. 定义大包工头（Supervisor）
这是整个系统的大脑。
```python
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system",
     # 详细的规则说明：
     # 1. 流程：Researcher → Analyst → FINISH
     # 2. 如果分析师总结了，必须输出 FINISH
     # 最后一句话要求：只输出下一个执行者的名字！
    ),
    MessagesPlaceholder(variable_name="messages"),
])
```
Supervisor **不干具体的活，手里也没有工具**。它的节点被激活时，只会看着桌上的历史聊天记录，结合脑墙上的“三条铁律规定”，回答出下一个流转对象的字符串名（Researcher、Analyst 或 FINISH）。

### 4. 星型拓扑路线图建立 (Hub & Spoke Graph)
```python
# 规定死规矩：员工一旦完成手里的活，必须马上交还给老板过目
workflow.add_edge("Researcher", "Supervisor")
workflow.add_edge("Analyst", "Supervisor")

# 老板看完后，根据信封上的 next 名字，决定下一个派给谁干，或者下班 (FINISH)
workflow.add_conditional_edges("Supervisor", lambda x: x["next"], ...)
```
这个极其优美的结构意味着：员工与员工之间绝不直接对接扯皮。所有的工作流向，完全由中央调度中心（Supervisor）控制。

### 5. 【亮点剖析】死循环的工程级防护体系
如果你完全信任大模型（老板），大模型一旦犯傻，可能会让 Analyst 重新审视 Analyst，然后再审视 Analyst，陷入无限分析的死循环。

看看这段精妙的防御代码：
```python
last_speaker = state.get("last_speaker", "")
# 如果老板让刚干完活的同一名员工接着干（且不是要下班结束任务）：
if next_node == last_speaker and next_node != "FINISH":
    logger.warning("⚠️ [Supervisor] 检测到死循环风险！强制终止。")
    next_node = "FINISH"
```
我们在 Python 代码层面，强行剥夺了 LLM 的控制权。如果识别到逻辑风险，直接覆盖 `next_node`，强行把系统拉到 `FINISH`。在真实的生产系统中，**永远不要把百分之百的流程流转权力交给大模型的自由发散**，一定要加代码级的安全兜底。

---

### 总结整个流程闭环
1. 任务发给 **Supervisor**。它阅读任务：“研究一下 Deepseek并总结”。判断当前手里没资料，输出：`next = Researcher`。
2. 球传给了 **Researcher**。它启动工具连通维基百科检索了一通，并把结果放入全局 `messages`。完成后，强制交回给 Supervisor。
3. **Supervisor** 再次被唤醒。看着刚才研究员搜出的一大车资料，觉得有依据了可以分析了。输出 `next = Analyst`。
4. **Analyst** 开始工作，基于以上内容提取要点，输出华丽的总结。完成后，交回给 Supervisor。
5. **Supervisor** 再次被唤醒，看到了分析师刚刚出具的最终研究报告，触碰到“铁律第2条”，于是满意地输出：`FINISH`。
6. Graph 到达 `END` 节点，任务圆满结束。
