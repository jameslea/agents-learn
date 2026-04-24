# 实验 1.4：微调实验室 (Fine-tuning Lab)

> **目标**：真枪实刀地跑通从数据准备到模型微调（SFT + DPO）的全流程。

## 一、 环境搭建 (Environment Setup)

由于微调涉及的底层库（`torch`, `transformers`, `trl`）常与 Agent 框架产生依赖冲突，本实验室使用独立的虚拟环境。

### 1. 创建虚拟环境
在当前目录下执行：
```bash
python3 -m venv venv_ft
source venv_ft/bin/activate
```

### 2. 安装核心依赖
使用清华镜像源以提速并避免 SSL 问题：
```bash
pip install --upgrade pip
pip install torch transformers trl peft accelerate bitsandbytes datasets -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

## 二、 实验内容
1. **`data_gen.py`**：手动构造高质量的 SFT 与 DPO 数据集。
2. **`train_sft.py`**：执行 **LoRA (低秩适配)** 微调。这是目前最推荐的轻量化方案，仅更新 ~1% 的参数。
3. **`train_full.py`**：执行 **全量 (Full)** 微调。更新 100% 的模型参数，用于对比资源消耗和训练速度。
4. **`train_dpo.py`**：执行直接偏好优化 (DPO)，通过对比学习纠正模型的死循环坏习惯。

## 三、 深度实验：LoRA vs 全量微调
你可以分别运行 `train_sft.py` 和 `train_full.py`。
*   **观察点 A**：`trainable params` (可训练参数量)。LoRA 应该比全量少 100 倍以上。
*   **观察点 B**：显存/内存占用。在全量微调时，你会看到内存占用显著飙升。
*   **观察点 C**：保存的模型大小。LoRA 仅几 MB，全量模型约 1GB。
