import os


def run_cleanup(path):
    # 示例问题：命令拼接会引入注入风险。
    os.system("rm -rf " + path)


def parse_value(raw):
    try:
        return int(raw)
    except:
        return 0

