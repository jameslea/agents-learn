from smolagents.local_python_executor import LocalPythonExecutor

# 模拟一个带有加法工具的环境
def dummy_tool(a, b):
    return a + b

# 初始化 smolagents 的本地执行器
executor = LocalPythonExecutor(
    additional_authorized_imports=[],  # 不允许任何额外导入
    additional_functions={"add": dummy_tool}
)

def test_code(code_string, description):
    print(f"\n--- 测试场景: {description} ---")
    print(f"代码内容: {code_string}")
    try:
        # 执行代码
        result = executor(code_string)
        print(f"✅ 执行结果: {result}")
    except Exception as e:
        # 捕获并打印沙盒的拦截信息
        print(f"❌ 拦截成功! 错误原因: {e}")

# 场景 1: 安全代码
test_code("add(1, 2) + 10", "简单合法的加法计算")

# 场景 2: 试图访问危险模块 (os)
test_code("import os; os.system('ls')", "试图执行系统命令 (import os)")

# 场景 3: 试图进行非法导入 (math，虽然 math 默认安全，但如果没在 authorized_imports 里也会被拦截)
test_code("import math; math.sqrt(16)", "试图导入未授权的模块 (math)")

# 场景 4: 试图遍历敏感信息
test_code("globals()", "试图访问全局命名空间")
