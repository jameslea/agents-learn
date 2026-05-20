from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CORE = PROJECT_ROOT / "runtime_core"

ALLOWED_RUNTIME_IMPORTS = {
    "artifact": {"artifact", "context"},
    "context": {"artifact", "context", "memory", "task"},
    "execution": {"artifact", "context", "execution", "memory", "observability", "task"},
    "memory": {"context", "memory"},
    "observability": {"observability", "task"},
    "task": {"task"},
}


def test_runtime_core_has_expected_top_level_packages() -> None:
    package_names = {
        path.name
        for path in RUNTIME_CORE.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }

    assert package_names == {
        "artifact",
        "context",
        "execution",
        "memory",
        "observability",
        "task",
    }


def test_runtime_core_imports_respect_documented_boundaries() -> None:
    violations: list[str] = []

    for source_path in RUNTIME_CORE.rglob("*.py"):
        source_package = source_path.relative_to(RUNTIME_CORE).parts[0]
        tree = ast.parse(source_path.read_text(encoding="utf-8"))

        for imported_module in _runtime_core_imports(tree):
            imported_package = imported_module.split(".")[1]
            allowed_packages = ALLOWED_RUNTIME_IMPORTS[source_package]
            if imported_package not in allowed_packages:
                violations.append(
                    f"{source_path.relative_to(PROJECT_ROOT)} imports {imported_module}; "
                    f"{source_package} may only import {sorted(allowed_packages)}"
                )

    assert violations == []


def test_runtime_core_does_not_depend_on_scenarios() -> None:
    violations: list[str] = []

    for source_path in RUNTIME_CORE.rglob("*.py"):
        text = source_path.read_text(encoding="utf-8")
        if "scenarios." in text or "practice-projects/06-agent-runtime-core/scenarios" in text:
            violations.append(str(source_path.relative_to(PROJECT_ROOT)))

    assert violations == []


def _runtime_core_imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("runtime_core."):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("runtime_core."):
                imports.append(node.module)
    return imports
