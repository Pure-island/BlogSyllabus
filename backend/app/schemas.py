from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ArticleAnalysisStatus,
    DifficultyLevel,
    FetchStatus,
    ItemAnalysisStatus,
    JobPhase,
    JobStatus,
    JobType,
    ReadingStage,
    ReadingStatus,
    SourceType,
)


class MessageResponse(BaseModel):
    message: str


class SourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    rss_url: Optional[str] = Field(default=None, max_length=500)
    source_type: SourceType = SourceType.RSS
    language: str = Field(default="zh-CN", max_length=32)
    priority: int = Field(default=50, ge=0, le=1000)
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    rss_url: Optional[str] = Field(default=None, max_length=500)
    source_type: Optional[SourceType] = None
    language: Optional[str] = Field(default=None, max_length=32)
    priority: Optional[int] = Field(default=None, ge=0, le=1000)
    is_active: Optional[bool] = None


class SourceRead(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_fetched_at: Optional[datetime]
    last_fetch_status: FetchStatus
    last_fetch_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    article_count: int = 0


class SourceCheckResponse(BaseModel):
    message: str
    feed_title: Optional[str] = None
    entry_count: int = 0


class SourceFetchResponse(BaseModel):
    message: str
    inserted_count: int
    deduplicated_count: int
    total_entries: int


class ArticleBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=800)
    published_at: Optional[datetime] = None
    author: Optional[str] = Field(default=None, max_length=200)
    raw_summary: Optional[str] = Field(default=None, max_length=2000)
    content_excerpt: Optional[str] = Field(default=None, max_length=5000)
    difficulty: Optional[DifficultyLevel] = None
    stage: Optional[ReadingStage] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    status: ReadingStatus = ReadingStatus.PLANNED
    is_core: bool = False
    core_score: Optional[float] = Field(default=None, ge=0, le=1)
    core_reason: Optional[str] = Field(default=None, max_length=2000)
    checkpoint_questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ArticleCreate(ArticleBase):
    source_id: Optional[int] = None
    source_name_snapshot: Optional[str] = Field(default=None, max_length=120)


class ArticleUpdate(BaseModel):
    difficulty: Optional[DifficultyLevel] = None
    stage: Optional[ReadingStage] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    status: Optional[ReadingStatus] = None
    is_core: Optional[bool] = None
    core_score: Optional[float] = Field(default=None, ge=0, le=1)
    core_reason: Optional[str] = Field(default=None, max_length=2000)
    checkpoint_questions: Optional[list[str]] = None
    raw_summary: Optional[str] = Field(default=None, max_length=2000)
    content_excerpt: Optional[str] = Field(default=None, max_length=5000)
    tags: Optional[list[str]] = None


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: Optional[int]
    source_name_snapshot: Optional[str]
    analysis_status: ArticleAnalysisStatus
    analysis_error: Optional[str]
    last_analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class BatchAnalyzeRequest(BaseModel):
    article_ids: Optional[list[int]] = None


class SettingsPayload(BaseModel):
    llm_provider_name: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_enabled: bool = False
    ui_language: str = "zh-CN"


class CurriculumResponse(BaseModel):
    foundation: list[ArticleRead] = Field(default_factory=list)
    core: list[ArticleRead] = Field(default_factory=list)
    frontier: list[ArticleRead] = Field(default_factory=list)
    update: list[ArticleRead] = Field(default_factory=list)
    unassigned: list[ArticleRead] = Field(default_factory=list)


class TodayResponse(BaseModel):
    generated_at: datetime
    primary_article: Optional[ArticleRead] = None
    secondary_article: Optional[ArticleRead] = None
    candidate_count: int = 0


class ProgressBucket(BaseModel):
    label: str
    count: int


class SourceProgressBucket(BaseModel):
    source_id: Optional[int]
    source_name: str
    total: int
    completed: int
    in_progress: int


class ProgressResponse(BaseModel):
    total_articles: int
    completed_articles: int
    in_progress_articles: int
    stage_breakdown: list[ProgressBucket]
    status_breakdown: list[ProgressBucket]
    tag_breakdown: list[ProgressBucket]
    source_breakdown: list[SourceProgressBucket]


class ReadingLogCreate(BaseModel):
    article_id: int
    read_date: date = Field(default_factory=date.today)
    status_after_read: ReadingStatus = ReadingStatus.PLANNED
    one_sentence_summary: Optional[str] = Field(default=None, max_length=2000)
    key_insight: Optional[str] = Field(default=None, max_length=2000)
    open_question: Optional[str] = Field(default=None, max_length=2000)
    next_action: Optional[str] = Field(default=None, max_length=2000)


class ReadingLogRead(ReadingLogCreate):
    id: int
    article_title: str
    article_url: Optional[str] = None
    created_at: datetime


class ManualSourceDraft(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    language: str = Field(default="zh-CN", max_length=32)
    priority: int = Field(default=50, ge=0, le=1000)
    is_active: bool = True


class ArticleImportCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=800)
    author: Optional[str] = Field(default=None, max_length=200)
    published_at: Optional[datetime] = None
    raw_summary: Optional[str] = Field(default=None, max_length=2000)
    content_excerpt: Optional[str] = Field(default=None, max_length=5000)
    source_name_snapshot: Optional[str] = Field(default=None, max_length=120)


class ArticleImportInvalidItem(BaseModel):
    raw: str
    reason: str


class ArticleImportPreviewRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=500000)
    use_llm_fallback: bool = False


class ArticleImportPreviewResponse(BaseModel):
    parsed_items: list[ArticleImportCandidate] = Field(default_factory=list)
    duplicate_items: list[ArticleImportCandidate] = Field(default_factory=list)
    invalid_items: list[ArticleImportInvalidItem] = Field(default_factory=list)
    total_items: int = 0
    importable_count: int = 0
    duplicate_count: int = 0
    invalid_count: int = 0
    used_llm_fallback: bool = False


class ArticleImportBatchPayload(BaseModel):
    items: list[ArticleImportCandidate] = Field(default_factory=list)
    source_id: Optional[int] = None
    new_source: Optional[ManualSourceDraft] = None
    analyze_after_import: bool = False


class ArticleImportBatchResponse(BaseModel):
    inserted_count: int
    duplicate_count: int
    skipped_count: int
    source_id: Optional[int] = None
    analyze_job_id: Optional[int] = None


class WeeklyPlannedArticleMetadata(BaseModel):
    article_id: int
    topic_key: Optional[str] = None
    track_type: str
    sequence_rank: int
    reason: str = ""


class WeeklyPlannedArticleRead(BaseModel):
    article: ArticleRead
    topic_key: Optional[str] = None
    track_type: str
    sequence_rank: int
    reason: str = ""


class WeeklyReviewRead(BaseModel):
    id: int
    week_start: date
    generated_plan: Optional[str]
    generated_review: Optional[str]
    primary_article_ids: list[int] = Field(default_factory=list)
    supplemental_article_ids: list[int] = Field(default_factory=list)
    primary_topic_key: Optional[str] = None
    supplemental_topic_key: Optional[str] = None
    article_plan_metadata: list[WeeklyPlannedArticleMetadata] = Field(default_factory=list)
    primary_articles: list[WeeklyPlannedArticleRead] = Field(default_factory=list)
    supplemental_articles: list[WeeklyPlannedArticleRead] = Field(default_factory=list)
    created_at: datetime


class ImportJobItemRead(BaseModel):
    id: int
    source_id: Optional[int]
    source_name: Optional[str] = None
    status: JobStatus
    phase: JobPhase
    total_entries: int
    inserted_entries: int
    deduplicated_entries: int
    analysis_status: ItemAnalysisStatus
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class ImportJobRead(BaseModel):
    id: int
    job_type: JobType
    status: JobStatus
    phase: JobPhase
    total_sources: int
    processed_sources: int
    successful_sources: int
    failed_sources: int
    inserted_articles: int
    deduplicated_articles: int
    pending_analysis_articles: int
    analyzed_articles: int
    failed_analysis_articles: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    items: list[ImportJobItemRead] = Field(default_factory=list)
