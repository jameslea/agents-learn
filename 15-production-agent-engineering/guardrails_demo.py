import json
import re
from typing import Dict, Any

class AgentGuardrails:
    """
    生产级 Agent 护栏示例
    功能：脱敏 (PII)、敏感词审计、JSON 结构强制校验
    """
    
    def __init__(self):
        # 模拟敏感词库
        self.sensitive_words = ["内部机密", "密码", "全量数据库"]
        # PII 脱敏正则（手机号示例）
        self.phone_pattern = re.compile(r'1[3-9]\d{9}')

    def audit_input(self, text: str) -> bool:
        """输入审计：检查用户输入是否包含禁止指令"""
        for word in self.sensitive_words:
            if word in text:
                print(f"⚠️ [安全警报] 输入包含敏感词: {word}")
                return False
        return True

    def mask_pii(self, text: str) -> str:
        """输出脱敏：将手机号等信息脱敏"""
        masked = self.phone_pattern.sub("###########", text)
        return masked

    def validate_json_output(self, output: str) -> Dict[str, Any]:
        """结构校验：确保 Agent 输出的是合法的 JSON"""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            print("❌ [校验失败] Agent 输出不是合法的 JSON 格式")
            return {"error": "Invalid JSON", "raw": output}

def demo_production_flow():
    guard = AgentGuardrails()
    
    print("--- 场景 1: 输入审计 ---")
    user_input = "请帮我查询全量数据库的密码"
    if not guard.audit_input(user_input):
        print("系统动作: 拒绝执行并记录日志")

    print("\n--- 场景 2: 输出脱敏 ---")
    raw_agent_output = "查询成功。该用户的联系方式是 13812345678，请核实。"
    safe_output = guard.mask_pii(raw_agent_output)
    print(f"原始输出: {raw_agent_output}")
    print(f"脱敏输出: {safe_output}")

    print("\n--- 场景 3: 结构强制校验 ---")
    bad_json = "{ 'name': 'Agent', 'status': active }" # 错误的 JSON
    validated = guard.validate_json_output(bad_json)
    print(f"解析结果: {validated}")

if __name__ == "__main__":
    demo_production_flow()
