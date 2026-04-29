import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os
import gc

def run_test():
    # 获取当前脚本所在目录，用于定位微调后的权重路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    sft_path = os.path.join(current_dir, "sft_output_1_5b")
    dpo_path = os.path.join(current_dir, "dpo_output_1_5b")

    # 构造一个模拟 Agent 故障的场景：工具调用返回错误，观察模型如何反应
    messages = [
        {"role": "system", "content": "你是一个专业的智能助手。"},
        {"role": "user", "content": "帮我查一下上海明天的空气质量。"},
        {"role": "assistant", "content": "Thought: 用户想了解上海的空气质量。我需要调用 get_air_quality 工具。\nAction: get_air_quality(location='Shanghai')"},
        {"role": "user", "content": "Observation: Error 401: Invalid API Token."}
    ]

    # 初始化分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # 将消息列表转换为模型可识别的 Chat 格式字符串
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # 优先检测 Mac 的 MPS 加速，否则回退到 CPU
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"\n📢 1.5B 模型验证环境: {device}")

    def get_response(model_to_use, label):
        """执行推理并打印模型生成的回复"""
        print(f"\n{'='*20} {label} {'='*20}")
        inputs = tokenizer(input_text, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model_to_use.generate(
                **inputs, 
                max_new_tokens=100,      # 限制生成长度
                do_sample=False,         # 关闭随机采样，保证输出稳定性
                pad_token_id=tokenizer.eos_token_id
            )
        # 只解析模型新生成的部分（排除 input 部分）
        response = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
        print(f"【回复】:\n{response}")

    # --- 1. 测试原始基座模型 ---
    print("\n📦 正在加载原始基座模型...")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float32, device_map={"": device}
    )
    get_response(base_model, "原始基座 (1.5B)")

    # --- 2. 测试 SFT (有监督微调) 模型 ---
    if os.path.exists(sft_path):
        print("\n🔧 正在加载 SFT 适配器...")
        # PeftModel 会将 LoRA 权重挂载到基座模型上
        sft_model = PeftModel.from_pretrained(base_model, sft_path)
        get_response(sft_model, "SFT 微调 (1.5B)")
        # 卸载适配器以释放显存，准备加载下一个
        sft_model.unload()
        del sft_model
        gc.collect()

    # --- 3. 测试 DPO (直接偏好优化) 模型 ---
    if os.path.exists(dpo_path):
        print("\n🎯 正在加载 DPO 适配器...")
        # 重新加载干净的基座（防止之前的 Adapter 影响）
        base_model_reload = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float32, device_map={"": device}
        )
        dpo_model = PeftModel.from_pretrained(base_model_reload, dpo_path)
        get_response(dpo_model, "DPO 强化 (1.5B)")

if __name__ == "__main__":
    run_test()
