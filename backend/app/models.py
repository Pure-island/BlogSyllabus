from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlalchemy import JSON, Column, Enum as SQLEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReadingStage(StrEnum):
    FOUNDATION = "foundation"
    CORE = "core"
    FRONTIER = "frontier"
    UPDATE = "update"


class ReadingStatus(StrEnum):
    PLANNED = "planned"
    SKIMMED = "skimmed"
    DEEP_READ = "deep_read"
    REVIEWED = "reviewed"
    MASTERED = "mastered"


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FetchStatus(StrEnum):
    IDLE = "idle"
    SUCCESS = "success"
    FAILED = "failed"


class SourceType(StrEnum):
    MANUAL = "manual"
    RSS = "rss"


class ArticleAnalysisStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


class JobType(StrEnum):
    FETCH_ACTIVE_SOURCES = "fetch_active_sources"
    FETCH_SOURCE = "fetch_source"
    ANALYZE_BATCH = "analyze_batch"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    BLOCKED = "blocked"


class JobPhase(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    DEDUPING = "deduping"
    INSERTING = "inserting"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"


class ItemAnalysisStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    rss_url: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String(length=500),
            nullable=True,
            unique=True,
            index=True,
        ),
    )
    source_type: SourceType = Field(
        default=SourceType.RSS,
        sa_column=Column(
            SQLEnum(
                SourceType,
                values_callable=lambda members: [member.value for member in members],
                native_enum=False,
            ),
            nullable=False,
            default=SourceType.RSS,
        ),
    )
    language: str = Field(default="zh-CN", max_length=32)
    priority: int = Field(default=50, ge=0, le=1000)
    is_active: bool = Field(default=True)
    last_fetched_at: Optional[datetime] = None
    last_fetch_status: FetchStatus = Field(default=FetchStatus.IDLE)
    last_fetch_error: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    articles: list["Article"] = Relationship(back_populates="source")


class Article(SQLModel, table=True):
    __tablename__ = "articles"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
    )
    source_name_snapshot: Optional[str] = Field(default=None, max_length=120)
    title: str = Field(index=True, min_length=1, max_length=300)
    url: str = Field(index=True, max_length=800, sa_column_kwargs={"unique": True})
    published_at: Optional[datetime] = None
    author: Optional[str] = Field(default=None, max_length=200)
    raw_summary: Optional[str] = Field(default=None, max_length=2000)
    content_excerpt: Optional[str] = Field(default=None, max_length=5000)
    difficulty: Optional[DifficultyLevel] = None
    stage: Optional[ReadingStage] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    status: ReadingStatus = Field(default=ReadingStatus.PLANNED)
    is_core: bool = Field(default=False)
    core_score: Optional[float] = Field(default=None, ge=0, le=1)
    core_reason: Optional[str] = Field(default=None, max_length=2000)
    checkpoint_questions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    analysis_status: ArticleAnalysisStatus = Field(default=ArticleAnalysisStatus.PENDING)
    analysis_error: Optional[str] = Field(default=None, max_length=2000)
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    source: Optional[Source] = Relationship(back_populates="articles")
    tags: list["ArticleTag"] = Relationship(back_populates="article")


class ArticleTag(SQLModel, table=True):
    __tablename__ = "article_tags"
    __table_args__ = (UniqueConstraint("article_id", "tag", name="uq_article_tag"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    tag: str = Field(max_length=80)

    article: Article = Relationship(back_populates="tags")


class ArticleRelation(SQLModel, table=True):
    __tablename__ = "article_relations"

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    prerequisite_article_id: int = Field(foreign_key="articles.id")
    relation_type: str = Field(default="prerequisite", max_length=80)


class ReadingLog(SQLModel, table=True):
    __tablename__ = "reading_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    read_date: date = Field(default_factory=date.today)
    status_after_read: ReadingStatus = Field(default=ReadingStatus.PLANNED)
    one_sentence_summary: Optional[str] = Field(default=None, max_length=2000)
    key_insight: Optional[str] = Field(default=None, max_length=2000)
    open_question: Optional[str] = Field(default=None, max_length=2000)
    next_action: Optional[str] = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now)


class WeeklyReview(SQLModel, table=True):
    __tablename__ = "weekly_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    week_start: date = Field(index=True)
    generated_plan: Optional[str] = Field(default=None, max_length=10000)
    generated_review: Optional[str] = Field(default=None, max_length=10000)
    primary_article_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    supplemental_article_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    primary_topic_key: Optional[str] = Field(default=None, max_length=200)
    supplemental_topic_key: Optional[str] = Field(default=None, max_length=200)
    article_plan_metadata: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(
        sa_column=Column("key", String(length=120), nullable=False, unique=True, index=True)
    )
    value: str = Field(default="", max_length=4000)
    updated_at: datetime = Field(default_factory=utc_now)


class ImportJob(SQLModel, table=True):
    __tablename__ = "import_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: JobType = Field(default=JobType.FETCH_ACTIVE_SOURCES)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    phase: JobPhase = Field(default=JobPhase.QUEUED)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    total_sources: int = Field(default=0)
    processed_sources: int = Field(default=0)
    successful_sources: int = Field(default=0)
    failed_sources: int = Field(default=0)
    inserted_articles: int = Field(default=0)
    deduplicated_articles: int = Field(default=0)
    pending_analysis_articles: int = Field(default=0)
    analyzed_articles: int = Field(default=0)
    failed_analysis_articles: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    items: list["ImportJobItem"] = Relationship(back_populates="job")


class ImportJobItem(SQLModel, table=True):
    __tablename__ = "import_job_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="import_jobs.id")
    source_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
    )
    status: JobStatus = Field(default=JobStatus.QUEUED)
    phase: JobPhase = Field(default=JobPhase.QUEUED)
    total_entries: int = Field(default=0)
    inserted_entries: int = Field(default=0)
    deduplicated_entries: int = Field(default=0)
    analysis_status: ItemAnalysisStatus = Field(default=ItemAnalysisStatus.PENDING)
    error_message: Optional[str] = Field(default=None, max_length=2000)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    job: ImportJob = Relationship(back_populates="items")
