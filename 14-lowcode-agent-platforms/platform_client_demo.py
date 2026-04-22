import os
import requests
import json

class DifyClient:
    """
    Dify 工作流/应用集成客户端示例
    展示如何通过代码调用低代码平台的“大脑”
    """
    def __init__(self, api_key: str = None, base_url: str = "https://api.dify.ai/v1"):
        self.api_key = api_key or os.getenv("DIFY_API_KEY", "YOUR_DIFY_API_KEY")
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_message(self, query: str, user_id: str = "dev_user", conversation_id: str = ""):
        """调用 Dify 聊天应用接口"""
        url = f"{self.base_url}/chat-messages"
        data = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking", # 或 streaming
            "conversation_id": conversation_id,
            "user": user_id
        }
        
        print(f"🚀 正在向 Dify 发送请求: {query}")
        
        # 实际运行环境若无 Key 会跳过请求演示
        if "YOUR_DIFY" in self.api_key:
            print("💡 [提示] 未配置 DIFY_API_KEY，此处仅展示请求结构：")
            print(json.dumps(data, indent=2))
            return {"answer": "模拟结果：低代码平台已收到请求并处理完成。"}

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

if __name__ == "__main__":
    client = DifyClient()
    
    # 示例交互
    response = client.chat_message("你好，请简述低代码 Agent 平台的优势")
    
    print("\n--- Dify 响应内容 ---")
    print(response.get("answer", "No answer found"))
