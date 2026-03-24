"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import type { Article, ArticlePayload, Source } from "@/lib/types";

const emptyArticle: ArticlePayload = {
  title: "",
  url: "",
  source_id: null,
  source_name_snapshot: null,
  published_at: null,
  author: null,
  raw_summary: null,
  content_excerpt: null,
  difficulty: null,
  stage: null,
  estimated_minutes: null,
  status: "planned",
  is_core: false,
  checkpoint_questions: [],
};

export function InboxPage() {
  const { dictionary } = useI18n();
  const [articles, setArticles] = useState<Article[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    source_id: "",
    status: "",
    difficulty: "",
  });
  const [form, setForm] = useState<ArticlePayload>(emptyArticle);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (filters.source_id) params.set("source_id", filters.source_id);
      if (filters.status) params.set("status", filters.status);
      if (filters.difficulty) params.set("difficulty", filters.difficulty);

      const [sourceList, inbox] = await Promise.all([
        api.listSources(),
        api.listInbox(params),
      ]);
      setSources(sourceList);
      setArticles(inbox);
    } catch (fetchError) {
      setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load inbox.");
    } finally {
      setLoading(false);
    }
  }, [filters.difficulty, filters.source_id, filters.status]);

  useEffect(() => {
    void load();
  }, [load]);

  const sourceLookup = useMemo(
    () => new Map(sources.map((source) => [source.id, source.name])),
    [sources],
  );

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await api.createArticle(form);
      setMessage(dictionary.successSaved);
      setForm(emptyArticle);
      await load();
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Create failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Inbox"
        title={dictionary.inboxTitle}
        description={dictionary.inboxDescription}
      />

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <form
          onSubmit={submit}
          className="rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_45px_rgba(15,23,42,0.08)]"
        >
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-slate-950">
              {dictionary.manualArticle}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {dictionary.inboxDescription}
            </p>
          </div>

          <div className="space-y-4">
            <TextField
              label={dictionary.articleTitle}
              value={form.title}
              onChange={(value) => setForm((current) => ({ ...current, title: value }))}
              required
            />
            <TextField
              label={dictionary.articleUrl}
              value={form.url}
              onChange={(value) => setForm((current) => ({ ...current, url: value }))}
              required
            />
            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">{dictionary.articleSource}</span>
              <select
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
                value={form.source_id ?? ""}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    source_id: event.target.value ? Number(event.target.value) : null,
                  }))
                }
              >
                <option value="">{dictionary.sourceUnknown}</option>
                {sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </label>
            <TextField
              label={dictionary.articleAuthor}
              value={form.author ?? ""}
              onChange={(value) => setForm((current) => ({ ...current, author: value || null }))}
            />
            <TextField
              label={dictionary.articleSummary}
              value={form.raw_summary ?? ""}
              onChange={(value) => setForm((current) => ({ ...current, raw_summary: value || null }))}
              multiline
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="mt-6 rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {saving ? dictionary.loading : dictionary.save}
          </button>
        </form>

        <div className="space-y-4">
          {message ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {message}
            </div>
          ) : null}
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}

          <div className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-[0_16px_45px_rgba(15,23,42,0.08)]">
            <div className="grid gap-3 md:grid-cols-3">
              <FilterSelect
                label={dictionary.articleSource}
                value={filters.source_id}
                onChange={(value) => setFilters((current) => ({ ...current, source_id: value }))}
                options={[
                  { value: "", label: "All" },
                  ...sources.map((source) => ({ value: String(source.id), label: source.name })),
                ]}
              />
              <FilterSelect
                label={dictionary.formStatus}
                value={filters.status}
                onChange={(value) => setFilters((current) => ({ ...current, status: value }))}
                options={[
                  { value: "", label: "All" },
                  { value: "planned", label: "planned" },
                  { value: "skimmed", label: "skimmed" },
                  { value: "deep_read", label: "deep_read" },
                ]}
              />
              <FilterSelect
                label={dictionary.formDifficulty}
                value={filters.difficulty}
                onChange={(value) => setFilters((current) => ({ ...current, difficulty: value }))}
                options={[
                  { value: "", label: "All" },
                  { value: "beginner", label: "beginner" },
                  { value: "intermediate", label: "intermediate" },
                  { value: "advanced", label: "advanced" },
                ]}
              />
            </div>
          </div>

          {loading ? (
            <div className="rounded-[28px] border border-slate-200/70 bg-white/90 px-6 py-12 text-sm text-slate-500 shadow-[0_16px_45px_rgba(15,23,42,0.08)]">
              {dictionary.loading}
            </div>
          ) : articles.length === 0 ? (
            <EmptyState title={dictionary.empty} description={dictionary.inboxDescription} />
          ) : (
            articles.map((article) => (
              <article
                key={article.id}
                className="rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_45px_rgba(15,23,42,0.08)]"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-xl font-semibold text-slate-950">
                        {article.title}
                      </h3>
                      <StatusBadge label={article.status} />
                    </div>
                    <p className="mt-3 text-sm text-slate-600">
                      {sourceLookup.get(article.source_id ?? -1) ||
                        article.source_name_snapshot ||
                        dictionary.sourceUnknown}
                    </p>
                    <a
                      className="mt-2 inline-flex text-sm font-medium text-sky-700 hover:text-sky-900"
                      href={article.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {article.url}
                    </a>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {article.difficulty ? (
                      <StatusBadge label={article.difficulty} tone="warning" />
                    ) : null}
                    {article.stage ? (
                      <StatusBadge label={article.stage} tone="success" />
                    ) : (
                      <StatusBadge label="inbox" tone="neutral" />
                    )}
                  </div>
                </div>

                {article.raw_summary ? (
                  <p className="mt-4 text-sm leading-7 text-slate-600">
                    {article.raw_summary}
                  </p>
                ) : null}
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  required = false,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  multiline?: boolean;
}) {
  const className =
    "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white";

  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-slate-700">{label}</span>
      {multiline ? (
        <textarea
          className={`${className} min-h-28 resize-y`}
          value={value}
          required={required}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <input
          className={className}
          value={value}
          required={required}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </label>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-slate-700">{label}</span>
      <select
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={`${label}-${option.value}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
