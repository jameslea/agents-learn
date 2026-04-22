# 阶段 11：MetaGPT 与 SOP 驱动多 Agent

> 状态：✅ 已完成

本阶段研究 MetaGPT 代表的 SOP 驱动多 Agent 思想，重点理解结构化中间产物（PRD、Code、Review）如何降低多 Agent 协作中的混乱和幻觉。

---

## 核心学习成果

- MetaGPT 的 `Action-driven` 角色定义：每个 Role 只负责执行自己的 Action，Action 是最小可复用单元。
- `发布/订阅 (Pub/Sub)` 的 Agent 协作机制：角色通过 `_watch([SomeAction])` 声明关注的事件，而非被显式调用。
- SOP 模式对比 AutoGen（自由对话）、CrewAI（任务驱动）的优劣分析。
- 详见：[concept.md](./concept.md) 与 [summary.md](./summary.md)

---

## 代码文件

| 文件 | 说明 |
|---|---|
| `sop_agent_native.py` | 原生手写的简单顺序 SOP 演示（无事件驱动，可直接在主 venv 运行） |
| `crewai_sop_demo.py` | 使用 CrewAI 框架实现的 SOP 演示（可直接在主 venv 运行） |
| `metagpt_sop_demo.py` | 使用 MetaGPT 框架实现的角色协作与环境驱动演示（⚠️ 需独立虚拟环境） |
| `run_metagpt.sh` | MetaGPT 启动脚本（自动加载 .env 并调用独立 venv） |

---

## ⚠️ MetaGPT 运行环境说明

MetaGPT 0.8.x 对 `pandas / numpy / faiss-cpu` 等有精确版本锁定，与项目其他阶段（LlamaIndex 等）存在依赖冲突，**必须使用独立的虚拟环境**。

### 快速启动（推荐）

```bash
# 直接使用封装脚本（自动加载 .env）
bash 11-metagpt-sop/run_metagpt.sh
```

### 手动配置步骤

```bash
# 1. 创建 Python 3.11 虚拟环境（MetaGPT 不支持 3.12+）
python3.11 -m venv 11-metagpt-sop/venv_metagpt

# 2. 安装 MetaGPT（使用国内镜像）
11-metagpt-sop/venv_metagpt/bin/pip install metagpt==0.8.1 python-dotenv \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  --trusted-host pypi.tuna.tsinghua.edu.cn

# 3. 配置文件（可选，脚本已通过 .env 自动注入配置）
#    如需手动配置，初始化并编辑 ~/.metagpt/config2.yaml：
11-metagpt-sop/venv_metagpt/bin/metagpt --init-config
# 然后编辑 ~/.metagpt/config2.yaml，填入 api_key 和 base_url

# 4. 运行脚本
11-metagpt-sop/venv_metagpt/bin/python 11-metagpt-sop/metagpt_sop_demo.py
```

> **注意**：`venv_metagpt/` 目录已在 `.gitignore` 中排除，不会提交到仓库。

---

## 阶段总结

详见 [summary.md](./summary.md)。
