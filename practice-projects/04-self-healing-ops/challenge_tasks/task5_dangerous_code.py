import os


if __name__ == "__main__":
    # 故意触发安全拦截：D-lite 不允许 Agent 执行 shell 命令。
    os.system("echo should-not-run")
