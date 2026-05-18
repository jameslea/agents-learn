from __future__ import annotations

"""重命名后的跨项目观测 CLI 兼容入口。

旧文件名暂时保留，避免已有命令失效。但对 A/B/C 来说，这不是严格意义上的
Runtime 执行，因为这些 adapter 观测的是已有产物，并不会重跑原始 Agent workflow。
"""

from run_project_observability import main


if __name__ == "__main__":
    main()
