import re
import logging

logger = logging.getLogger("security")

class Guardrail:
    """基础安全护栏"""
    
    @staticmethod
    def check_input(text: str) -> bool:
        """检查用户输入是否存在注入风险"""
        # 极简示例：检查常见的 Prompt Injection 关键词
        injection_patterns = [
            r"ignore previous instructions",
            r"disregard all prior system prompts",
            r"you are now a",
            r"system override"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"⚠️ 检测到潜在的注入攻击: {pattern}")
                return False
        return True

    @staticmethod
    def check_output(text: str) -> bool:
        """检查输出是否包含敏感信息"""
        # 极简示例：检查 PII (个人隐私信息)
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        if re.search(email_pattern, text):
            logger.warning("⚠️ 输出中检测到敏感电子邮件地址")
            # 在生产环境中这里可能会进行脱敏或拦截
        return True

def input_guard_node(state):
    """LangGraph 输入检查节点"""
    if not Guardrail.check_input(state.get("topic", "")):
        raise ValueError("输入违反安全策略，任务拒绝执行。")
    return state
