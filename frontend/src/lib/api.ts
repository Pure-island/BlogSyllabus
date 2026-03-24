import type {
  Article,
  ArticlePayload,
  SettingsPayload,
  Source,
  SourcePayload,
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
    request<{
      message: string;
      inserted_count: number;
      deduplicated_count: number;
      total_entries: number;
    }>(`/sources/${id}/fetch`, {
      method: "POST",
    }),
  listInbox: (params?: URLSearchParams) =>
    request<Article[]>(`/inbox${params?.toString() ? `?${params.toString()}` : ""}`),
  createArticle: (payload: ArticlePayload) =>
    request<Article>("/articles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listArticles: () => request<Article[]>("/articles"),
  getSettings: () => request<SettingsPayload>("/settings"),
  updateSettings: (payload: SettingsPayload) =>
    request<SettingsPayload>("/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
};
