import torch
import os
import time
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset

"""
🧠 知识点：什么是全量微调 (Full Fine-tuning)？

相对于 LoRA 这种“打补丁”式的微调，全量微调是“全脑重塑”。
1. 原理：模型内部数以亿计的所有神经元参数都处于“待更新”状态。
2. 优点：模型学习能力达到理论上限，可以进行极其深刻的行为改变。
3. 缺点：显存消耗恐怖，训练极其缓慢，且容易产生“灾难性遗忘”（为了学新知识丢了老本）。

💻 硬件资源预估 (以 Qwen2.5-0.5B 为例)：
- 显存/内存需求：约为模型参数大小的 4-8 倍。
- 0.5B 模型全量训练：建议 12GB+ 内存。
- 7B 模型全量训练：建议 80GB+ 显存 (通常需要多张 A100/H100)。
- M4 Pro (48G)：可以非常轻松地运行此脚本。
"""

def train_full():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_name = "Qwen/Qwen2.5-0.5B"
    dataset_path = os.path.join(current_dir, "sft_train.jsonl")
    output_dir = os.path.join(current_dir, "full_output")

    # 1. 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # 2. 设备自动识别
    if torch.backends.mps.is_available():
        device = "mps"
        print("💻 检测到 Apple Silicon (MPS)，正在开启全量训练...")
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    # 3. 加载完整模型
    # 注意：全量训练时，所有参数的 requires_grad 默认为 True
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map={"": device}
    )

    # 📊 参数量统计：你会看到这里的参数量是 LoRA 的几百倍
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"📊 当前【全量训练】可训练参数量: {trainable_params:,}")
    print(f"提示：0.5B 代表约 5 亿个参数。LoRA 模式通常只需训练约 120 万个。")

    # 4. 数据预处理
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    
    # 格式化函数：将 JSONL 中的对话转化为模型可理解的输入
    def formatting_prompts_func(example):
        text = f"System: {example['messages'][0]['content']}\nUser: {example['messages'][1]['content']}\nAssistant: {example['messages'][2]['content']}"
        return tokenizer(text, truncation=True, padding="max_length", max_length=512)

    tokenized_dataset = dataset.map(formatting_prompts_func)

    # 5. 训练参数配置 (TrainingArguments)
    # 💡 架构师调参指南：
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,   # M4 Pro 用户可尝试调至 4 或 8
        gradient_accumulation_steps=4,  # 累计多少次梯度更新一次参数
        
        # ⚠️ 关键点：全量训练的学习率必须【非常小】
        # 如果设为 2e-4 (LoRA级别)，模型会瞬间崩溃，输出乱码。
        # 建议值：5e-6 到 2e-5 之间。
        learning_rate=2e-5, 
        
        max_steps=20,                   # 实验目的，只跑 20 步
        logging_steps=5,
        save_strategy="no",
        fp16=False,                     # Mac 建议关闭
        report_to="none"
    )

    # 6. 使用原生 Trainer
    # 注意：这里没有传入 peft_config，说明是全量微调
    trainer = Trainer(
        model=model,
        train_dataset=tokenized_dataset,
        args=training_args,
    )

    # 7. 开始训练并计时
    print("🚀 正在点火，开始全量大脑重塑...")
    start_time = time.time()
    trainer.train()
    end_time = time.time()
    
    print(f"✅ 全量训练 20 步耗时: {end_time - start_time:.2f} 秒")
    print(f"💾 完整模型保存中 (这会占用约 1GB 磁盘)...")
    # model.save_pretrained(output_dir) # 如需保存完整模型，取消此行注释

if __name__ == "__main__":
    train_full()
