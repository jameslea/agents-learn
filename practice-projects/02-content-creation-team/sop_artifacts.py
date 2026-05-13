from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union

class ContentOutline(BaseModel):
    """由产品经理生成的报告大纲"""
    title: str = Field(..., description="报告标题")
    target_audience: str = Field(..., description="目标受众")
    sections: List[str] = Field(..., description="各个章节的标题或关键词")
    key_points: Union[str, List[str]] = Field(..., description="整篇报告需要覆盖的核心要点")

    @field_validator('key_points')
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class ResearchMaterial(BaseModel):
    """由研究员搜集的素材"""
    section_name: str = Field(..., description="对应的章节名称")
    raw_data: str = Field(..., description="搜集到的原始事实、数据或引用，每条关键数据后括号标注来源序号如(来源1)")
    sources: List[str] = Field(..., description="参考来源链接或文献，与 raw_data 中序号一一对应")
    source_quality: List[str] = Field(
        default_factory=list,
        description="每个来源的可信度等级：tier_1/tier_2/tier_3，与 sources 一一对应"
    )
    source_notes: List[str] = Field(
        default_factory=list,
        description="每个来源的可信度说明或降级原因，与 sources 一一对应"
    )

    @field_validator('source_quality')
    @classmethod
    def normalize_source_quality(cls, v):
        allowed = {"tier_1", "tier_2", "tier_3"}
        return [item if item in allowed else "tier_3" for item in v]

    def model_post_init(self, __context):
        if len(self.source_quality) < len(self.sources):
            self.source_quality.extend(["tier_3"] * (len(self.sources) - len(self.source_quality)))
        if len(self.source_notes) < len(self.sources):
            self.source_notes.extend(["未提供来源可信度说明"] * (len(self.sources) - len(self.source_notes)))

class ResearchReport(BaseModel):
    """整合后的研究摘要"""
    materials: List[ResearchMaterial] = Field(..., description="所有章节的搜集素材列表")

class DraftContent(BaseModel):
    """由撰稿人生成的初稿"""
    title: str
    content_markdown: str = Field(
        ...,
        description="Markdown 格式的正文内容，要求 3000 字以上，每条数据点后内联标注来源编号如 [1]"
    )
    word_count: int = Field(..., description="正文字数，要求不低于 3000")
    citations: List[str] = Field(
        default_factory=list,
        description="行文中引用的所有来源 URL 列表，按引用顺序排列"
    )

class ReviewFeedback(BaseModel):
    """由评审员生成的评审意见"""
    is_approved: bool = Field(..., description="是否通过审核")
    suggestions: List[str] = Field(..., description="整体修改建议列表")
    specific_issues: List[str] = Field(
        default_factory=list,
        description="章节级别的具体问题，格式：'章节名: 具体问题描述'"
    )
    target_agent: Optional[str] = Field(None, description="建议修改的角色 (researcher/writer)")

class TeamState(BaseModel):
    """团队协作的完整状态"""
    topic: str
    outline: Optional[ContentOutline] = None
    research_report: Optional[ResearchReport] = None
    draft: Optional[DraftContent] = None
    draft_history: List[DraftContent] = Field(default_factory=list, description="历次生成的初稿版本记录")
    latest_feedback: Optional[ReviewFeedback] = None
    history_summary: str = ""
    review_count: int = 0
    history: List[str] = []
