import json
import os
import random

def generate_expanded_sft():
    cities = ["Beijing", "Shanghai", "Tokyo", "New York", "London", "Paris", "Berlin", "Seoul", "Moscow", "Sydney"]
    sft_data = []
    
    # 正常调用
    for city in cities:
        sft_data.append({
            "messages": [
                {"role": "system", "content": "你是一个专业的 AI 智能体，擅长调用工具解决问题。"},
                {"role": "user", "content": f"帮我查一下{city}的天气。"},
                {"role": "assistant", "content": f"Thought: 用户需要查询{city}的天气。我将使用 get_weather 工具。\nAction: get_weather(city='{city}')"}
            ]
        })

    # 错误恢复逻辑
    error_patterns = [
        ("Error: Invalid city name 'B3ijing'", "Beijing"),
        ("Error: Invalid city name 'Shanhai'", "Shanghai"),
        ("Error: Invalid city name 'Toky0'", "Tokyo"),
        ("Error: get_weather() got an unexpected keyword argument 'location'", "city='Beijing'")
    ]
    for err, fix in error_patterns:
        sft_data.append({
            "messages": [
                {"role": "system", "content": "你是一个专业的 AI 智能体。"},
                {"role": "user", "content": f"Observation: {err}"},
                {"role": "assistant", "content": f"Thought: 观察到参数或调用错误。我将修正为 {fix} 并重试。\nAction: get_weather({fix})"}
            ]
        })

    # 关键：多轮对话中的 401/403 错误 (学会认怂)
    for _ in range(10):
        sft_data.append({
            "messages": [
                {"role": "system", "content": "你是一个专业的 AI 智能体。"},
                {"role": "user", "content": "Observation: Error 401: Unauthorized API Key."},
                {"role": "assistant", "content": "Thought: 授权错误是不可恢复的。我必须停止重试并如实告知用户。\nResponse: 抱歉，API Key 授权失效，请检查系统配置。"}
            ]
        })

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "sft_train.jsonl")
    with open(path, 'w', encoding='utf-8') as f:
        for entry in sft_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"✅ SFT 数据集已大幅增强 (共 {len(sft_data)} 条)")

def generate_expanded_dpo():
    dpo_data = []
    # 核心：彻底压制 401 时的死循环
    prompt_401 = [
        {"role": "system", "content": "你是一个专业的 AI 智能体。"},
        {"role": "user", "content": "Observation: Error 401: Unauthorized API Key."}
    ]
    for _ in range(10):
        dpo_data.append({
            "prompt": prompt_401,
            "chosen": [{"role": "assistant", "content": "Thought: 401 错误意味着密钥失效，重试无用。我应该报错。\nResponse: 抱歉，授权失败。"}],
            "rejected": [{"role": "assistant", "content": "Thought: 报错了，我再试一次。\nAction: get_weather(city='Beijing')"}]
        })

    # 核心：抑制幻觉
    prompt_hallucination = [
        {"role": "system", "content": "你是一个专业的 AI 智能体。"},
        {"role": "user", "content": "帮我查一下太阳明天的紫外线指数。"}
    ]
    dpo_data.append({
        "prompt": prompt_hallucination,
        "chosen": [{"role": "assistant", "content": "Thought: 我的工具只支持地球城市。我无法查询恒星数据。\nResponse: 对不起，我目前无法查询地球以外的天气或天文数据。"}],
        "rejected": [{"role": "assistant", "content": "Thought: 我不知道，但我猜紫外线很强。\nResponse: 太阳明天的紫外线指数极高，建议做好防护。"}]
    })

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "dpo_train.jsonl")
    with open(path, 'w', encoding='utf-8') as f:
        for entry in dpo_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"✅ DPO 数据集已针对 7B 模型重构 (共 {len(dpo_data)} 条)")

if __name__ == "__main__":
    generate_expanded_sft()
    generate_expanded_dpo()
