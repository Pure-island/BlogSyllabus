import type {
  Article,
  ArticleImportBatchPayload,
  ArticleImportBatchResponse,
  ArticleImportPreviewPayload,
  ArticleImportPreviewResponse,
  ArticlePayload,
  ArticleUpdatePayload,
  BatchAnalyzePayload,
  CurriculumResponse,
  ImportJob,
  MessageResponse,
  ProgressResponse,
  ReadingLog,
  ReadingLogPayload,
  SettingsPayload,
  Source,
  SourcePayload,
  TodayResponse,
  WeeklyReview,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "/backend-api";

type RequestOptions = RequestInit & {
  skipJson?: boolean;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function buildPath(path: string, params?: URLSearchParams) {
  const query = params?.toString();
  return `${API_BASE}${path}${query ? `?${query}` : ""}`;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (options.skipJson) {
    if (!response.ok) {
      throw new ApiError(response.statusText, response.status);
    }
    return undefined as T;
  }

  const payload = await response.json();
  if (!response.ok) {
    throw new ApiError(payload.message || response.statusText, response.status);
  }

  return payload as T;
}

export const api = {
  listSources: () => request<Source[]>("/sources"),
  createSource: (payload: SourcePayload) =>
    request<Source>("/sources", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateSource: (id: number, payload: Partial<SourcePayload>) =>
    request<Source>(`/sources/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteSource: (id: number) =>
    request<void>(`/sources/${id}`, {
      method: "DELETE",
      skipJson: true,
    }),
  testSource: (id: number) =>
    request<{ message: string; feed_title?: string; entry_count: number }>(
      `/sources/${id}/test`,
      {
        method: "POST",
      },
    ),
  fetchSource: (id: number) =>
    request<{ message: string; inserted_count: number; deduplicated_count: number; total_entries: number }>(
      `/sources/${id}/fetch`,
      {
        method: "POST",
      },
    ),
  createBulkImportJob: () =>
    request<MessageResponse>("/imports/sources/fetch-active", {
      method: "POST",
    }),
  createSourceImportJob: (id: number) =>
    request<MessageResponse>(`/imports/sources/${id}/fetch`, {
      method: "POST",
    }),
  listImportJobs: () => request<ImportJob[]>("/imports/jobs"),
  getImportJob: (id: number) => request<ImportJob>(`/imports/jobs/${id}`),
  retryImportJob: (id: number) =>
    request<MessageResponse>(`/imports/jobs/${id}/retry`, {
      method: "POST",
    }),
  listInbox: (params?: URLSearchParams) =>
    request<Article[]>(buildPath("/inbox", params).replace(API_BASE, "")),
  createArticle: (payload: ArticlePayload) =>
    request<Article>("/articles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewArticleImport: (payload: ArticleImportPreviewPayload) =>
    request<ArticleImportPreviewResponse>("/articles/import-preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  importArticleBatch: (payload: ArticleImportBatchPayload) =>
    request<ArticleImportBatchResponse>("/articles/import-batch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listArticles: (params?: URLSearchParams) =>
    request<Article[]>(buildPath("/articles", params).replace(API_BASE, "")),
  updateArticle: (id: number, payload: ArticleUpdatePayload) =>
    request<Article>(`/articles/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  analyzeArticle: (id: number) =>
    request<Article>(`/articles/${id}/analyze`, {
      method: "POST",
    }),
  analyzeBatch: (payload: BatchAnalyzePayload = {}) =>
    request<MessageResponse & { job_id: number }>("/articles/analyze-batch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCurriculum: () => request<CurriculumResponse>("/curriculum"),
  getToday: () => request<TodayResponse>("/today"),
  generateToday: () =>
    request<TodayResponse>("/today/generate", {
      method: "POST",
    }),
  getProgress: () => request<ProgressResponse>("/progress"),
  listReadingLogs: () => request<ReadingLog[]>("/reading-logs"),
  createReadingLog: (payload: ReadingLogPayload) =>
    request<ReadingLog>("/reading-logs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCurrentWeekly: () => request<WeeklyReview | null>("/weekly/current"),
  generateWeekly: () =>
    request<WeeklyReview>("/weekly/generate", {
      method: "POST",
    }),
  getWeeklyHistory: () => request<WeeklyReview[]>("/weekly/history"),
  getSettings: () => request<SettingsPayload>("/settings"),
  updateSettings: (payload: SettingsPayload) =>
    request<SettingsPayload>("/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testSettingsConnection: (payload: SettingsPayload) =>
    request<MessageResponse>("/settings/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
