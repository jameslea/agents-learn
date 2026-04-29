import torch
import os
import inspect
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig
from datasets import load_dataset

def train_dpo():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    dataset_path = os.path.join(current_dir, "dpo_train.jsonl")
    output_dir = os.path.join(current_dir, "dpo_output_1_5b")

    # 1. 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 2. 设备检测
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"🚀 正在对 1.5B 模型进行 DPO 优化...")

    # 3. 加载模型
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map={"": device}
    )
    
    # 4. 配置 LoRA (保持 r=16 与 SFT 一致)
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 5. 加载数据集
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    # 6. DPOConfig 调优
    dpo_config_params = inspect.signature(DPOConfig.__init__).parameters
    config_kwargs = {
        "output_dir": output_dir,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "learning_rate": 5e-5,
        "max_steps": 40, 
        "logging_steps": 5,
        "save_strategy": "no",
        "fp16": False,
        "report_to": "none",
        "beta": 0.1,
    }

    if "max_length" in dpo_config_params:
        config_kwargs["max_length"] = 512
    if "max_prompt_length" in dpo_config_params:
        config_kwargs["max_prompt_length"] = 256

    dpo_config = DPOConfig(**config_kwargs)

    # 7. 初始化 DPOTrainer
    trainer = DPOTrainer(
        model=model,
        ref_model=None, 
        args=dpo_config,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    # 8. 开始训练
    print(f"🧠 1.5B DPO 强化中...")
    trainer.train()
    
    # 9. 保存成果
    trainer.model.save_pretrained(output_dir)
    print(f"✅ 1.5B DPO 完成！保存至: {output_dir}")

if __name__ == "__main__":
    train_dpo()
