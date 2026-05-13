"""质量工具统一出口。

实际实现按职责拆在相邻模块中：
- url_utils: URL 基础工具
- source_quality: 来源分级、排序和来源质量提醒
- research_quality: 研究素材门禁
- references: 参考资料解析与重编号
- draft_quality: 草稿结构、字数和引用闭环门禁
- outline_evaluation: 大纲质量评估指标
- report_evaluation: 历史报告质量评估指标

保留本文件是为了兼容既有 `from utils.quality import ...` 调用。
"""

from utils.draft_quality import (
    count_report_units,
    has_report_title,
    list_item_count,
    numbered_section_blocks,
    numbered_section_count,
    structural_keyword_hits,
    subsection_blocks,
    subsection_count,
    validate_draft,
)
from utils.references import (
    REFERENCE_HEADING,
    normalize_draft_references,
    parse_reference_urls,
)
from utils.outline_evaluation import (
    OutlineQualityMetrics,
    evaluate_outline_quality,
    validate_outline,
)
from utils.report_evaluation import (
    ReportQualityMetrics,
    compare_reports,
    evaluate_report_quality,
)
from utils.research_quality import validate_research_report
from utils.source_quality import (
    HIGH_QUALITY_SOURCE_TIERS,
    SOURCE_TIER_RANK,
    infer_source_tier,
    ranked_source_records,
    source_quality_summary,
    source_quality_warnings,
)
from utils.url_utils import is_valid_url, unique_urls


__all__ = [
    "HIGH_QUALITY_SOURCE_TIERS",
    "OutlineQualityMetrics",
    "REFERENCE_HEADING",
    "ReportQualityMetrics",
    "SOURCE_TIER_RANK",
    "compare_reports",
    "count_report_units",
    "evaluate_outline_quality",
    "evaluate_report_quality",
    "has_report_title",
    "infer_source_tier",
    "is_valid_url",
    "list_item_count",
    "normalize_draft_references",
    "numbered_section_blocks",
    "numbered_section_count",
    "parse_reference_urls",
    "ranked_source_records",
    "source_quality_summary",
    "source_quality_warnings",
    "structural_keyword_hits",
    "subsection_blocks",
    "subsection_count",
    "unique_urls",
    "validate_draft",
    "validate_outline",
    "validate_research_report",
]
