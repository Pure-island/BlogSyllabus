export type ReadingStage =
  | "foundation"
  | "core"
  | "frontier"
  | "update";

export type ReadingStatus =
  | "planned"
  | "skimmed"
  | "deep_read"
  | "reviewed"
  | "mastered";

export type DifficultyLevel = "beginner" | "intermediate" | "advanced";
export type FetchStatus = "idle" | "success" | "failed";
export type LanguageCode = "zh-CN" | "en";

export type Source = {
  id: number;
  name: string;
  homepage_url: string | null;
  rss_url: string;
  category: string | null;
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
  checkpoint_questions: string[];
  created_at: string;
  updated_at: string;
};

export type SettingsPayload = {
  openai_api_key: string;
  openai_model: string;
  ui_language: LanguageCode;
  openai_enabled: boolean;
};

export type SourcePayload = {
  name: string;
  homepage_url: string | null;
  rss_url: string;
  category: string | null;
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
  checkpoint_questions: string[];
};
