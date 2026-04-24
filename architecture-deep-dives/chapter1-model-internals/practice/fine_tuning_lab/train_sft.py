import torch
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig
from datasets import load_dataset

"""
🚀 实验 1.4.1：SFT 有监督微调 (1.5B 模型版)

【核心目标】：
通过提供高质量的 ReAct (Thought-Action-Observation) 范文，让模型掌握 Agent 的思考节奏。
SFT 就像是让模型在特定的岗位上进行“岗前培训”，学会标准的业务术语和输出格式。

【针对 1.5B 模型的架构建议】：
- LoRA Rank (r=16)：1.5B 模型参数适中，16 秩足以捕捉其格式偏好，且不会导致过拟合。
- Learning Rate (1e-4)：相对于 0.5B，1.5B 更加稳健，可以使用稍大的步长。
"""

def train():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 我们选用 Qwen2.5-1.5B，它是目前在个人电脑上运行最平衡的模型：速度快、逻辑清。
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    dataset_path = os.path.join(current_dir, "sft_train.jsonl")
    output_dir = os.path.join(current_dir, "sft_output_1_5b")

    # 1. 加载分词器
    # trust_remote_code=True 是因为部分模型有自定义的 Tokenizer 实现。
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 2. 设备检测
    # M4 Pro 48G 下，mps 能够提供极高的吞吐量。
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"🚀 M4 Pro 猛兽已就位！正在使用 {device} 训练 1.5B 模型...")

    # 3. 加载模型
    # 48G 内存足以支撑 float32 全精度加载 1.5B 模型。
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map={"": device}
    )

    # 4. 配置 LoRA (低秩适配器)
    # 这就像是在原书上贴的“动作指引”便签纸。
    peft_config = LoraConfig(
        r=16,          # 秩：便签纸的宽度，16 是 1.5B 模型的黄金值。
        lora_alpha=32, # 缩放系数：通常为 r 的两倍，决定便签内容的影响力。
        target_modules=["q_proj", "v_proj"], # 针对注意力机制的核心权重进行微调。
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 5. 加载数据集
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    # 6. 定义格式化函数
    # 作用：利用模型内置的聊天模板（Chat Template）将消息列表转为带特殊 Token 的文本。
    def formatting_prompts_func(example):
        return tokenizer.apply_chat_template(example['messages'], tokenize=False, add_generation_prompt=False)

    # 7. SFTConfig 调优 (针对 2025 版 TRL)
    sft_config = SFTConfig(
        output_dir=output_dir,
        max_length=512,                # 限制输入长度，节省显存并提速。
        per_device_train_batch_size=2, # M4 Pro 可以同时处理 2 个样本。
        gradient_accumulation_steps=4, # 累计 4 次梯度更新一次，模拟 Batch Size = 8。
        learning_rate=1e-4,            # 学习率：步子跨度。
        max_steps=80,                  # 训练步数。
        logging_steps=10,
        save_strategy="no",            # 实验期间不保存庞大的中间检查点。
        fp16=False,                    # Mac 上关闭混合精度，使用全精度 float32。
        report_to="none"
    )

    # 8. 初始化训练器
    # 注意：最新版使用 processing_class 替代 tokenizer 以支持多模态扩展。
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        formatting_func=formatting_prompts_func,
        processing_class=tokenizer,
        args=sft_config,
    )

    # 9. 开始训练
    print(f"🔥 正在对 1.5B 模型执行 SFT 精调...")
    trainer.train()
    
    # 10. 保存 LoRA 权重
    # 我们只保存那个几 MB 的补丁，推理时再动态挂载。
    trainer.model.save_pretrained(output_dir)
    print(f"✅ 1.5B SFT 完成！权重保存至: {output_dir}")

if __name__ == "__main__":
    train()
