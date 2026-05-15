from __future__ import annotations

from pathlib import Path

from state import ErrorKind, ErrorSummary


class RepairAgent:
    """D-lite 当前使用的规则型修复 Agent。

    这里暂时不调用 LLM，是为了先验证执行、分类、修复、验证、trace
    这条自愈管线是否可靠。后续替换成 LLM Agent 时，也应保持同样的接口。
    """

    def repair(self, path: Path, error: ErrorSummary) -> tuple[bool, str]:
        """根据错误分类尝试生成最小源码改动。"""
        original = path.read_text(encoding="utf-8")
        repaired = original
        summary = f"No rule matched {error.kind.value}."

        if error.kind == ErrorKind.IMPORT_ERROR:
            repaired, summary = self._repair_import_error(original, error)
        elif error.kind == ErrorKind.SYNTAX_ERROR:
            repaired, summary = self._repair_syntax_error(original, error)
        elif error.kind == ErrorKind.TIMEOUT:
            repaired, summary = self._repair_timeout(original, error)
        elif error.kind in {ErrorKind.RUNTIME_ERROR, ErrorKind.ASSERTION_ERROR}:
            repaired, summary = self._repair_runtime_or_assertion(original, error)
        elif error.kind == ErrorKind.UNKNOWN:
            repaired, summary = self._repair_unknown(original, error)

        if repaired == original:
            return False, summary

        path.write_text(repaired, encoding="utf-8")
        return True, summary

    def _repair_import_error(self, source: str, error: ErrorSummary) -> tuple[str, str]:
        """示例修复：删除明显拼错且未使用的 import。"""
        if "requestz" in source:
            return source.replace("import requestz\n\n", ""), "Removed unused misspelled import 'requestz'."
        return source, f"No import repair rule for: {error.message}"

    def _repair_syntax_error(self, source: str, error: ErrorSummary) -> tuple[str, str]:
        """示例修复：处理缺少右括号这类局部语法错误。"""
        lines = source.splitlines()
        line_index = (error.line_number or len(lines)) - 1
        if 0 <= line_index < len(lines):
            line = lines[line_index]
            if line.count("(") > line.count(")"):
                lines[line_index] = line + ")"
                return "\n".join(lines) + "\n", f"Balanced missing ')' on line {line_index + 1}."
        if source.count("(") > source.count(")"):
            return source.rstrip() + ")\n", "Balanced trailing missing ')'."
        return source, f"No syntax repair rule for: {error.message}"

    def _repair_timeout(self, source: str, error: ErrorSummary) -> tuple[str, str]:
        """示例修复：给循环变量补进度，打破无限循环。"""
        if "while current < 3:" in source and "values.append(current)\n    return values" in source:
            repaired = source.replace(
                "        values.append(current)\n    return values",
                "        values.append(current)\n        current += 1\n    return values",
            )
            return repaired, "Added loop progress increment after appending current."
        return source, f"No timeout repair rule for: {error.message}"

    def _repair_runtime_or_assertion(self, source: str, error: ErrorSummary) -> tuple[str, str]:
        """示例修复：运行时错误和断言失败都必须通过再次执行确认。"""
        if "def safe_divide(a, b):\n    return a / b" in source:
            repaired = source.replace(
                "def safe_divide(a, b):\n    return a / b",
                "def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b",
            )
            return repaired, "Added zero-division guard returning None."
        if "def clamp(value, minimum, maximum):\n    return value" in source:
            repaired = source.replace(
                "def clamp(value, minimum, maximum):\n    return value",
                "def clamp(value, minimum, maximum):\n    if value < minimum:\n        return minimum\n    if value > maximum:\n        return maximum\n    return value",
            )
            return repaired, "Implemented lower and upper bounds in clamp."
        if "def get_user_email(users, user_id):\n    return users[user_id][\"email\"]" in source:
            repaired = source.replace(
                "def get_user_email(users, user_id):\n    return users[user_id][\"email\"]",
                "def get_user_email(users, user_id):\n    user = users.get(user_id)\n    if not user:\n        return None\n    return user.get(\"email\")",
            )
            return repaired, "Added missing-user guard and safe email lookup."
        if "def average(values):\n    return sum(values) / len(values)" in source:
            repaired = source.replace(
                "def average(values):\n    return sum(values) / len(values)",
                "def average(values):\n    if not values:\n        return 0\n    return sum(values) / len(values)",
            )
            return repaired, "Added empty-list guard returning 0."
        return source, f"No runtime/assertion repair rule for: {error.message}"

    def _repair_unknown(self, source: str, error: ErrorSummary) -> tuple[str, str]:
        """示例修复：处理当前分类器尚未细分的常见异常。"""
        return source, f"No unknown-error repair rule for: {error.message}"
