"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import type { Source, SourcePayload } from "@/lib/types";

const emptySource: SourcePayload = {
  name: "",
  homepage_url: "",
  rss_url: "",
  category: "",
  language: "zh-CN",
  priority: 50,
  is_active: true,
};

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
        {label}
      </div>
      <div className="mt-2 text-sm font-medium text-slate-700">{value}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-slate-700">{label}</span>
      <input
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function SourcesPage() {
  const { dictionary } = useI18n();
  const [sources, setSources] = useState<Source[]>([]);
  const [form, setForm] = useState<SourcePayload>(emptySource);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setSources(await api.listSources());
    } catch (fetchError) {
      setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load sources.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  const resetForm = () => {
    setForm(emptySource);
    setEditingId(null);
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (editingId) {
        await api.updateSource(editingId, form);
      } else {
        await api.createSource(form);
      }
      setMessage(dictionary.successSaved);
      resetForm();
      await loadSources();
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (source: Source) => {
    setEditingId(source.id);
    setForm({
      name: source.name,
      homepage_url: source.homepage_url,
      rss_url: source.rss_url,
      category: source.category,
      language: source.language,
      priority: source.priority,
      is_active: source.is_active,
    });
  };

  const removeSource = async (source: Source) => {
    if (!window.confirm(dictionary.confirmDelete)) return;

    try {
      await api.deleteSource(source.id);
      setMessage(dictionary.successDeleted);
      await loadSources();
    } catch (deleteError) {
      setError(deleteError instanceof ApiError ? deleteError.message : "Delete failed.");
    }
  };

  const runAction = async (source: Source, type: "test" | "fetch" | "toggle") => {
    try {
      setError(null);
      setMessage(null);

      if (type === "test") {
        const result = await api.testSource(source.id);
        setMessage(
          `${dictionary.successTested} ${result.feed_title ? `${result.feed_title} | ` : ""}${result.entry_count}`,
        );
      }

      if (type === "fetch") {
        const result = await api.fetchSource(source.id);
        setMessage(
          `${dictionary.successFetched} ${result.inserted_count}/${result.total_entries}`,
        );
      }

      if (type === "toggle") {
        await api.updateSource(source.id, { is_active: !source.is_active });
        setMessage(dictionary.successSaved);
      }

      await loadSources();
    } catch (actionError) {
      setError(actionError instanceof ApiError ? actionError.message : "Action failed.");
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Phase 2"
        title={dictionary.sourcesTitle}
        description={dictionary.sourcesDescription}
      />

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <form
          onSubmit={submit}
          className="rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_45px_rgba(15,23,42,0.08)]"
        >
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-slate-950">
              {editingId ? dictionary.edit : dictionary.add}
            </h3>
            <p className="mt-2 text-sm text-slate-600">{dictionary.sourcesDescription}</p>
          </div>

          <div className="space-y-4">
            <Field
              label={dictionary.formName}
              value={form.name}
              onChange={(value) => setForm((current) => ({ ...current, name: value }))}
              required
            />
            <Field
              label={dictionary.formHomepage}
              value={form.homepage_url ?? ""}
              onChange={(value) =>
                setForm((current) => ({ ...current, homepage_url: value }))
              }
            />
            <Field
              label={dictionary.formRss}
              value={form.rss_url}
              onChange={(value) => setForm((current) => ({ ...current, rss_url: value }))}
              required
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label={dictionary.formCategory}
                value={form.category ?? ""}
                onChange={(value) =>
                  setForm((current) => ({ ...current, category: value }))
                }
              />
              <Field
                label={dictionary.formLanguage}
                value={form.language}
                onChange={(value) =>
                  setForm((current) => ({ ...current, language: value }))
                }
              />
            </div>

            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">{dictionary.formPriority}</span>
              <input
                type="number"
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
                value={form.priority}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    priority: Number(event.target.value),
                  }))
                }
              />
            </label>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    is_active: event.target.checked,
                  }))
                }
              />
              {dictionary.formActive}
            </label>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {saving ? dictionary.loading : dictionary.save}
            </button>
            {editingId ? (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-full border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                {dictionary.cancel}
              </button>
            ) : null}
          </div>
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

          {loading ? (
            <div className="rounded-[28px] border border-slate-200/70 bg-white/90 px-6 py-12 text-sm text-slate-500 shadow-[0_16px_45px_rgba(15,23,42,0.08)]">
              {dictionary.loading}
            </div>
          ) : sources.length === 0 ? (
            <EmptyState title={dictionary.empty} description={dictionary.sourcesDescription} />
          ) : (
            sources.map((source) => (
              <article
                key={source.id}
                className="rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_45px_rgba(15,23,42,0.08)]"
              >
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-xl font-semibold text-slate-950">{source.name}</h3>
                      <StatusBadge
                        label={source.is_active ? dictionary.active : dictionary.paused}
                        tone={source.is_active ? "success" : "warning"}
                      />
                    </div>
                    <p className="mt-3 text-sm text-slate-600">{source.rss_url}</p>
                    {source.homepage_url ? (
                      <a
                        className="mt-2 inline-flex text-sm font-medium text-sky-700 hover:text-sky-900"
                        href={source.homepage_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.homepage_url}
                      </a>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(source)}
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {dictionary.edit}
                    </button>
                    <button
                      type="button"
                      onClick={() => void runAction(source, "test")}
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {dictionary.test}
                    </button>
                    <button
                      type="button"
                      onClick={() => void runAction(source, "fetch")}
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {dictionary.fetch}
                    </button>
                    <button
                      type="button"
                      onClick={() => void runAction(source, "toggle")}
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {source.is_active ? dictionary.paused : dictionary.active}
                    </button>
                    <button
                      type="button"
                      onClick={() => void removeSource(source)}
                      className="rounded-full border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50"
                    >
                      {dictionary.delete}
                    </button>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                  <Metric label={dictionary.formCategory} value={source.category || "-"} />
                  <Metric label={dictionary.formLanguage} value={source.language} />
                  <Metric label={dictionary.formPriority} value={String(source.priority)} />
                  <Metric label={dictionary.formArticleCount} value={String(source.article_count)} />
                  <Metric
                    label={dictionary.formLastFetched}
                    value={formatDate(source.last_fetched_at)}
                  />
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Metric
                    label={dictionary.formFetchStatus}
                    value={
                      source.last_fetch_status === "success"
                        ? dictionary.statusSuccess
                        : source.last_fetch_status === "failed"
                          ? dictionary.statusFailed
                          : dictionary.statusIdle
                    }
                  />
                  {source.last_fetch_error ? (
                    <p className="text-sm text-rose-700">
                      {dictionary.formFetchError}: {source.last_fetch_error}
                    </p>
                  ) : null}
                </div>
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
