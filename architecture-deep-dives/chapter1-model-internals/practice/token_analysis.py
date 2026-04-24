import tiktoken
from transformers import AutoTokenizer

def analyze_tokens(text, model_name, tokenizer_type="tiktoken"):
    print(f"\n--- Analyzing with {model_name} ({tokenizer_type}) ---")
    if tokenizer_type == "tiktoken":
        enc = tiktoken.encoding_for_model(model_name)
        tokens = enc.encode(text)
    else:
        # Use fast tokenizer if possible
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        tokens = tokenizer.encode(text)
    
    print(f"Text length: {len(text)} characters")
    print(f"Token count: {len(tokens)}")
    print(f"Characters per Token: {len(text) / len(tokens):.2f}")
    if len(tokens) < 20:
        print(f"Tokens: {tokens}")

if __name__ == "__main__":
    test_texts = {
        "English": "Artificial Intelligence is transforming the world of software engineering.",
        "Chinese": "人工智能正在改变软件工程的世界。",
        "Code": "def hello_world():\n    print('Hello, world!')"
    }

    # Compare GPT-4 (tiktoken) vs Qwen2.5 (transformers - localized for Chinese)
    models = [
        ("gpt-4", "tiktoken"),
        ("Qwen/Qwen2.5-7B-Instruct", "transformers")
    ]

    for label, text in test_texts.items():
        print(f"\n{'='*20} {label} {'='*20}")
        for model_name, t_type in models:
            try:
                analyze_tokens(text, model_name, t_type)
            except Exception as e:
                print(f"Error analyzing with {model_name}: {e}")

    # Prompt Caching Logic Demo (Pseudo-code logic)
    print(f"\n{'='*20} Prompt Caching Logic Demo {'='*20}")
    system_prompt = "You are a helpful assistant."
    tools = "Tools: [get_weather, get_stock_price]"
    user_query = "What is the weather in Tokyo?"
    
    prefix_1 = f"{system_prompt}\n{tools}\nUser: {user_query}"
    prefix_2 = f"{system_prompt}\n{tools}\nUser: What is the weather in Paris?"
    
    # In automatic prefix matching (DeepSeek/OpenAI), 
    # the common prefix "{system_prompt}\n{tools}\nUser: " would be cached.
    print(f"Prefix 1: ...{prefix_1[-30:]}")
    print(f"Prefix 2: ...{prefix_2[-30:]}")
    # If a dynamic ID is inserted at the START:
    prefix_fail = f"Session-ID: 12345\n{system_prompt}\n{tools}\nUser: {user_query}"
    print("\nWarning: Putting dynamic content like 'Session-ID' at the start kills Prompt Caching!")
