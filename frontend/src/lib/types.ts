export type ReadingStage = "foundation" | "core" | "frontier" | "update";

export type ReadingStatus =
  | "planned"
  | "skimmed"
  | "deep_read"
  | "reviewed"
  | "mastered";

export type DifficultyLevel = "beginner" | "intermediate" | "advanced";
export type FetchStatus = "idle" | "success" | "failed";
export type LanguageCode = "zh-CN" | "en";
export type SourceType = "manual" | "rss";
export type ArticleAnalysisStatus =
  | "pending"
  | "complete"
  | "failed"
  | "blocked";
export type JobType =
  | "fetch_active_sources"
  | "fetch_source"
  | "analyze_batch";
export type JobStatus =
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "partial_success"
  | "blocked";
export type JobPhase =
  | "queued"
  | "fetching"
  | "deduping"
  | "inserting"
  | "analysis_pending"
  | "analyzing"
  | "completed";
export type ItemAnalysisStatus =
  | "pending"
  | "complete"
  | "failed"
  | "blocked"
  | "skipped";

export type Source = {
  id: number;
  name: string;
  homepage_url: string | null;
  rss_url: string | null;
  source_type: SourceType;
  language: string;
  priority: number;
  is_active: boolean;
  last_fetched_at: string | null;
  last_fetch_status: FetchStatus;
  last_fetch_error: string | null;
  created_at: string;
  updated_at: string;
  article_count: number;
};

export type Article = {
  id: number;
  source_id: number | null;
  source_name_snapshot: string | null;
  title: string;
  url: string;
  published_at: string | null;
  author: string | null;
  raw_summary: string | null;
  content_excerpt: string | null;
  difficulty: DifficultyLevel | null;
  stage: ReadingStage | null;
  estimated_minutes: number | null;
  status: ReadingStatus;
  is_core: boolean;
  core_score: number | null;
  core_reason: string | null;
  checkpoint_questions: string[];
  tags: string[];
  analysis_status: ArticleAnalysisStatus;
  analysis_error: string | null;
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SettingsPayload = {
  llm_provider_name: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  llm_enabled: boolean;
  ui_language: LanguageCode;
};

export type SourcePayload = {
  name: string;
  homepage_url: string | null;
  rss_url: string | null;
  source_type: SourceType;
  language: string;
  priority: number;
  is_active: boolean;
};

export type ArticlePayload = {
  title: string;
  url: string;
  source_id: number | null;
  source_name_snapshot: string | null;
  published_at: string | null;
  author: string | null;
  raw_summary: string | null;
  content_excerpt: string | null;
  difficulty: DifficultyLevel | null;
  stage: ReadingStage | null;
  estimated_minutes: number | null;
  status: ReadingStatus;
  is_core: boolean;
  core_score: number | null;
  core_reason: string | null;
  checkpoint_questions: string[];
  tags: string[];
};

export type ArticleUpdatePayload = Partial<
  Pick<
    ArticlePayload,
    | "difficulty"
    | "stage"
    | "estimated_minutes"
    | "status"
    | "is_core"
    | "core_score"
    | "core_reason"
    | "checkpoint_questions"
    | "raw_summary"
    | "content_excerpt"
    | "tags"
  >
>;

export type BatchAnalyzePayload = {
  article_ids?: number[];
};

export type CurriculumResponse = {
  foundation: Article[];
  core: Article[];
  frontier: Article[];
  update: Article[];
  unassigned: Article[];
};

export type TodayResponse = {
  generated_at: string;
  primary_article: Article | null;
  secondary_article: Article | null;
  candidate_count: number;
};

export type ProgressBucket = {
  label: string;
  count: number;
};

export type SourceProgressBucket = {
  source_id: number | null;
  source_name: string;
  total: number;
  completed: number;
  in_progress: number;
};

export type ProgressResponse = {
  total_articles: number;
  completed_articles: number;
  in_progress_articles: number;
  stage_breakdown: ProgressBucket[];
  status_breakdown: ProgressBucket[];
  tag_breakdown: ProgressBucket[];
  source_breakdown: SourceProgressBucket[];
};

export type ReadingLogPayload = {
  article_id: number;
  read_date: string;
  status_after_read: ReadingStatus;
  one_sentence_summary: string | null;
  key_insight: string | null;
  open_question: string | null;
  next_action: string | null;
};

export type ReadingLog = ReadingLogPayload & {
  id: number;
  article_title: string;
  article_url: string | null;
  created_at: string;
};

export type WeeklyReview = {
  id: number;
  week_start: string;
  generated_plan: string | null;
  generated_review: string | null;
  primary_article_ids: number[];
  supplemental_article_ids: number[];
  primary_topic_key: string | null;
  supplemental_topic_key: string | null;
  article_plan_metadata: {
    article_id: number;
    topic_key: string | null;
    track_type: "primary" | "supplemental" | "skip";
    sequence_rank: number;
    reason: string;
  }[];
  primary_articles: {
    article: Article;
    topic_key: string | null;
    track_type: "primary" | "supplemental" | "skip";
    sequence_rank: number;
    reason: string;
  }[];
  supplemental_articles: {
    article: Article;
    topic_key: string | null;
    track_type: "primary" | "supplemental" | "skip";
    sequence_rank: number;
    reason: string;
  }[];
  created_at: string;
};

export type ImportJobItem = {
  id: number;
  source_id: number | null;
  source_name: string | null;
  status: JobStatus;
  phase: JobPhase;
  total_entries: number;
  inserted_entries: number;
  deduplicated_entries: number;
  analysis_status: ItemAnalysisStatus;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type ImportJob = {
  id: number;
  job_type: JobType;
  status: JobStatus;
  phase: JobPhase;
  total_sources: number;
  processed_sources: number;
  successful_sources: number;
  failed_sources: number;
  inserted_articles: number;
  deduplicated_articles: number;
  pending_analysis_articles: number;
  analyzed_articles: number;
  failed_analysis_articles: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  items: ImportJobItem[];
};

export type MessageResponse = {
  message: string;
};

export type ManualSourceDraft = {
  name: string;
  homepage_url: string | null;
  language: string;
  priority: number;
  is_active: boolean;
};

export type ArticleImportCandidate = {
  title: string;
  url: string;
  author: string | null;
  published_at: string | null;
  raw_summary: string | null;
  content_excerpt: string | null;
  source_name_snapshot: string | null;
};

export type ArticleImportInvalidItem = {
  raw: string;
  reason: string;
};

export type ArticleImportPreviewResponse = {
  parsed_items: ArticleImportCandidate[];
  duplicate_items: ArticleImportCandidate[];
  invalid_items: ArticleImportInvalidItem[];
  total_items: number;
  importable_count: number;
  duplicate_count: number;
  invalid_count: number;
  used_llm_fallback: boolean;
};

export type ArticleImportPreviewPayload = {
  raw_text: string;
  use_llm_fallback: boolean;
};

export type ArticleImportBatchPayload = {
  items: ArticleImportCandidate[];
  source_id: number | null;
  new_source: ManualSourceDraft | null;
  analyze_after_import: boolean;
};

export type ArticleImportBatchResponse = {
  inserted_count: number;
  duplicate_count: number;
  skipped_count: number;
  source_id: number | null;
  analyze_job_id: number | null;
};
