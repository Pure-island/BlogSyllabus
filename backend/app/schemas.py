from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import DifficultyLevel, FetchStatus, ReadingStage, ReadingStatus


class MessageResponse(BaseModel):
    message: str


class SourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    rss_url: str = Field(min_length=1, max_length=500)
    category: Optional[str] = Field(default=None, max_length=120)
    language: str = Field(default="zh-CN", max_length=32)
    priority: int = Field(default=50, ge=0, le=1000)
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    rss_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    category: Optional[str] = Field(default=None, max_length=120)
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
    checkpoint_questions: list[str] = Field(default_factory=list)


class ArticleCreate(ArticleBase):
    source_id: Optional[int] = None
    source_name_snapshot: Optional[str] = Field(default=None, max_length=120)


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: Optional[int]
    source_name_snapshot: Optional[str]
    created_at: datetime
    updated_at: datetime


class SettingsPayload(BaseModel):
    openai_api_key: str = ""
    openai_model: str = ""
    ui_language: str = "zh-CN"
    openai_enabled: bool = False
