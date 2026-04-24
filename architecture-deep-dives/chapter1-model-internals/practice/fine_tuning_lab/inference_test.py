import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os
import gc

def run_test():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    sft_path = os.path.join(current_dir, "sft_output_1_5b")
    dpo_path = os.path.join(current_dir, "dpo_output_1_5b")

    messages = [
        {"role": "system", "content": "你是一个专业的智能助手。"},
        {"role": "user", "content": "帮我查一下上海明天的空气质量。"},
        {"role": "assistant", "content": "Thought: 用户想了解上海的空气质量。我需要调用 get_air_quality 工具。\nAction: get_air_quality(location='Shanghai')"},
        {"role": "user", "content": "Observation: Error 401: Invalid API Token."}
    ]

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"\n📢 1.5B 模型验证环境: {device}")

    def get_response(model_to_use, label):
        print(f"\n{'='*20} {label} {'='*20}")
        inputs = tokenizer(input_text, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model_to_use.generate(
                **inputs, 
                max_new_tokens=100,
                do_sample=False, 
                pad_token_id=tokenizer.eos_token_id
            )
        response = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
        print(f"【回复】:\n{response}")

    # 测试基座
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float32, device_map={"": device}
    )
    get_response(base_model, "原始基座 (1.5B)")

    # 测试 SFT
    if os.path.exists(sft_path):
        sft_model = PeftModel.from_pretrained(base_model, sft_path)
        get_response(sft_model, "SFT 微调 (1.5B)")
        sft_model.unload()
        del sft_model
        gc.collect()

    # 测试 DPO
    if os.path.exists(dpo_path):
        base_model_reload = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float32, device_map={"": device}
        )
        dpo_model = PeftModel.from_pretrained(base_model_reload, dpo_path)
        get_response(dpo_model, "DPO 强化 (1.5B)")

if __name__ == "__main__":
    run_test()
