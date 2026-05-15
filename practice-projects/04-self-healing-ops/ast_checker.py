from __future__ import annotations

import ast
from pathlib import Path

from state import SafetyIssue


BLOCKED_IMPORTS = {"socket", "requests", "urllib", "httpx", "ftplib", "paramiko"}
# D-lite 只允许本地、可控的 Python 脚本执行；网络、文件破坏、动态执行都先拦截。
BLOCKED_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "os.system",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "shutil.rmtree",
}


def check_file(path: Path) -> list[SafetyIssue]:
    """静态扫描高风险语法。

    如果文件本身有语法错误，这里不抢先处理，交给执行/分类链路识别 SyntaxError。
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []

    issues: list[SafetyIssue] = []
    for node in ast.walk(tree):
        # import 和 from import 都只看顶层包名，例如 urllib.request -> urllib。
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", maxsplit=1)[0]
                if root_name in BLOCKED_IMPORTS:
                    issues.append(
                        SafetyIssue(
                            line_number=node.lineno,
                            kind="blocked_import",
                            message=f"Import of '{alias.name}' is not allowed in D-lite.",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".", maxsplit=1)[0]
            if root_name in BLOCKED_IMPORTS:
                issues.append(
                    SafetyIssue(
                        line_number=node.lineno,
                        kind="blocked_import",
                        message=f"Import from '{node.module}' is not allowed in D-lite.",
                    )
                )
        elif isinstance(node, ast.Call):
            # 将 os.system(...) 这类调用还原成可匹配的完整名字。
            call_name = _call_name(node.func)
            if call_name in BLOCKED_CALLS:
                issues.append(
                    SafetyIssue(
                        line_number=node.lineno,
                        kind="blocked_call",
                        message=f"Call to '{call_name}' is not allowed in D-lite.",
                    )
                )
    return issues


def _call_name(node: ast.AST) -> str:
    """把 AST 调用节点转换为字符串名称，如 subprocess.run。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
