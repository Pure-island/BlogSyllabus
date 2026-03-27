"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { labelForAnalysisStatus, labelForJobPhase, labelForJobStatus } from "@/lib/i18n";
import type { ImportJob, Source, SourcePayload, SourceType } from "@/lib/types";

const emptySource: SourcePayload = {
  name: "",
  homepage_url: "",
  rss_url: "",
  source_type: "rss",
  language: "zh-CN",
  priority: 50,
  is_active: true,
};

function formatDate(value: string | null, locale: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-subcard px-4 py-3">
      <div className="app-stat-label">{label}</div>
      <div className="mt-2 text-sm font-medium text-slate-700">{value}</div>
    </div>
  );
}

function SourceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-subcard px-4 py-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
        {label}
      </div>
      <div className="mt-2 text-base font-semibold text-slate-800">{value}</div>
    </div>
  );
}

function LinkCard({
  label,
  value,
  href,
}: {
  label: string;
  value: string;
  href?: string | null;
}) {
  const content = (
    <>
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
        {label}
      </div>
      <div className="mt-2 break-all text-sm font-medium text-slate-700">{value}</div>
    </>
  );

  if (!href) {
    return <div className="app-subcard p-4">{content}</div>;
  }

  return (
    <a
      className="app-subcard block p-4 transition hover:border-sky-200 hover:text-sky-800"
      href={href}
      target="_blank"
      rel="noreferrer"
    >
      {content}
    </a>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="app-field">
      <span className="app-field-label">{label}</span>
      <input
        className="app-input"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function SourcesPage() {
  const { dictionary, language } = useI18n();
  const [sources, setSources] = useState<Source[]>([]);
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [form, setForm] = useState<SourcePayload>(emptySource);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const labels = useMemo(
    () => ({
      sourceType: language === "zh-CN" ? "来源类型" : "Source type",
      rssSource: language === "zh-CN" ? "RSS 来源" : "RSS source",
      manualSource: language === "zh-CN" ? "手动来源" : "Manual source",
      rssHint:
        language === "zh-CN"
          ? "可抓取和订阅更新的来源"
          : "Can be fetched and updated from RSS.",
      manualHint:
        language === "zh-CN"
          ? "先手动导入文章，之后可补填 RSS 升级为订阅来源"
          : "Manual now, can be upgraded to an RSS source later.",
      rssOptional:
        language === "zh-CN"
          ? "手动来源可以先留空，后续再补填 RSS。"
          : "Manual sources can leave RSS empty and add it later.",
      unlinkedRss: language === "zh-CN" ? "未接入 RSS" : "RSS not configured",
      manualOnly: language === "zh-CN" ? "手动维护" : "Manual only",
      testRss: language === "zh-CN" ? "测试 RSS" : "Test RSS",
      fetchNow: language === "zh-CN" ? "立即抓取" : "Fetch now",
      syncFetch: language === "zh-CN" ? "同步抓取" : "Sync fetch",
      enableSource: language === "zh-CN" ? "启用来源" : "Enable source",
      disableSource: language === "zh-CN" ? "停用来源" : "Disable source",
      activeRssOnly:
        language === "zh-CN"
          ? "批量导入只会处理已启用的 RSS 来源。"
          : "Bulk import only runs for active RSS sources.",
      noRssActions:
        language === "zh-CN"
          ? "补填 RSS URL 并保存后，这个来源就会变成可订阅来源。"
          : "Add an RSS URL and save to upgrade this source into a subscribable RSS source.",
      sourceTypeValue: (type: SourceType) =>
        type === "rss"
          ? language === "zh-CN"
            ? "RSS"
            : "RSS"
          : language === "zh-CN"
            ? "手动"
            : "Manual",
    }),
    [language],
  );

  const loadSources = useCallback(async () => {
    const [sourceList, jobList] = await Promise.all([api.listSources(), api.listImportJobs()]);
    setSources(sourceList);
    setJobs(jobList);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        await loadSources();
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load sources.");
      }
    })();
  }, [loadSources]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void api.listImportJobs().then(setJobs).catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(timer);
  }, []);

  const latestJob = jobs[0] ?? null;

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
      const payload: SourcePayload = {
        ...form,
        rss_url: form.rss_url?.trim() || null,
      };
      if (editingId) {
        await api.updateSource(editingId, payload);
      } else {
        await api.createSource(payload);
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
      source_type: source.source_type,
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

  const runAction = async (source: Source, type: "test" | "fetch" | "toggle" | "sync") => {
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
        const result = await api.createSourceImportJob(source.id);
        setMessage(result.message);
      }
      if (type === "sync") {
        const result = await api.fetchSource(source.id);
        setMessage(`${dictionary.successFetched} ${result.inserted_count}/${result.total_entries}`);
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

  const runBulkImport = async () => {
    try {
      setError(null);
      setMessage(null);
      const result = await api.createBulkImportJob();
      setMessage(result.message);
      await loadSources();
    } catch (actionError) {
      setError(actionError instanceof ApiError ? actionError.message : "Action failed.");
    }
  };

  const retryJob = async (jobId: number) => {
    try {
      setError(null);
      setMessage(null);
      const result = await api.retryImportJob(jobId);
      setMessage(result.message);
      await loadSources();
    } catch (actionError) {
      setError(actionError instanceof ApiError ? actionError.message : "Action failed.");
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Sources"
        title={dictionary.sourcesTitle}
        description={dictionary.sourcesDescription}
        action={
          <button type="button" onClick={() => void runBulkImport()} className="app-button-primary">
            {dictionary.bulkImport}
          </button>
        }
      />

      <div className="mb-4 app-alert app-alert-warn">{labels.activeRssOnly}</div>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <form onSubmit={submit} className="app-panel p-6 sm:p-7">
          <div className="app-section-head">
            <p className="app-kicker">Source</p>
            <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">
              {editingId ? dictionary.edit : dictionary.add}
            </h3>
            <p className="app-copy mt-2">
              {form.source_type === "rss" ? labels.rssHint : labels.manualHint}
            </p>
          </div>

          <div className="space-y-4">
            <label className="app-field">
              <span className="app-field-label">{labels.sourceType}</span>
              <select
                className="app-select"
                value={form.source_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    source_type: event.target.value as SourceType,
                  }))
                }
              >
                <option value="rss">{labels.rssSource}</option>
                <option value="manual">{labels.manualSource}</option>
              </select>
            </label>

            <Field
              label={dictionary.formName}
              value={form.name}
              onChange={(value) => setForm((current) => ({ ...current, name: value }))}
            />
            <Field
              label={dictionary.formHomepage}
              value={form.homepage_url ?? ""}
              onChange={(value) => setForm((current) => ({ ...current, homepage_url: value }))}
            />
            <Field
              label={dictionary.formRss}
              value={form.rss_url ?? ""}
              onChange={(value) => setForm((current) => ({ ...current, rss_url: value }))}
              placeholder={form.source_type === "manual" ? labels.rssOptional : "https://example.com/feed.xml"}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label={dictionary.formLanguage}
                value={form.language}
                onChange={(value) => setForm((current) => ({ ...current, language: value }))}
              />
              <label className="app-field">
                <span className="app-field-label">{dictionary.formPriority}</span>
                <input
                  type="number"
                  className="app-input"
                  value={form.priority}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, priority: Number(event.target.value) }))
                  }
                />
              </label>
            </div>

            <label className="app-toggle">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm((current) => ({ ...current, is_active: event.target.checked }))
                }
              />
              {dictionary.formActive}
            </label>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={saving}
              className="app-button-primary disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {saving ? dictionary.loading : dictionary.save}
            </button>
            {editingId ? (
              <button type="button" onClick={resetForm} className="app-button-secondary">
                {dictionary.cancel}
              </button>
            ) : null}
          </div>
        </form>

        <div className="space-y-4">
          {message ? <div className="app-alert app-alert-success">{message}</div> : null}
          {error ? <div className="app-alert app-alert-error">{error}</div> : null}

          <div className="app-panel p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">{dictionary.latestJobs}</h3>
                <p className="mt-1 text-sm text-slate-600">{dictionary.latestJobDescription}</p>
              </div>
              {latestJob ? (
                <button
                  type="button"
                  onClick={() => void retryJob(latestJob.id)}
                  className="app-button-secondary"
                >
                  {dictionary.retry}
                </button>
              ) : null}
            </div>

            {!latestJob ? (
              <div className="mt-4">
                <EmptyState title={dictionary.noJobs} description={dictionary.latestJobDescription} />
              </div>
            ) : (
              <div className="mt-6 space-y-5">
                <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
                  <Metric label={dictionary.currentStatus} value={labelForJobStatus(language, latestJob.status)} />
                  <Metric label={dictionary.currentPhase} value={labelForJobPhase(language, latestJob.phase)} />
                  <Metric
                    label={dictionary.processedSources}
                    value={`${latestJob.processed_sources}/${latestJob.total_sources}`}
                  />
                  <Metric label={dictionary.insertedArticles} value={String(latestJob.inserted_articles)} />
                  <Metric label={dictionary.analyzedArticles} value={String(latestJob.analyzed_articles)} />
                </div>
                <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
                  <Metric label={dictionary.successfulSources} value={String(latestJob.successful_sources)} />
                  <Metric label={dictionary.failedSources} value={String(latestJob.failed_sources)} />
                  <Metric
                    label={dictionary.deduplicatedArticles}
                    value={String(latestJob.deduplicated_articles)}
                  />
                  <Metric label={dictionary.pendingAnalysis} value={String(latestJob.pending_analysis_articles)} />
                </div>
                {latestJob.error_message ? (
                  <p className="text-sm text-rose-700">{latestJob.error_message}</p>
                ) : null}

                <div className="space-y-3">
                  <div className="text-sm font-semibold text-slate-950">{dictionary.sourceProgress}</div>
                  {latestJob.items.map((item) => (
                    <div key={item.id} className="app-subcard p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium text-slate-900">
                          {item.source_name || dictionary.sourceUnknown}
                        </div>
                        <StatusBadge
                          label={labelForJobStatus(language, item.status)}
                          tone={
                            item.status === "failed"
                              ? "danger"
                              : item.status === "success"
                                ? "success"
                                : "warning"
                          }
                        />
                        <StatusBadge label={labelForJobPhase(language, item.phase)} />
                        <StatusBadge label={labelForAnalysisStatus(language, item.analysis_status)} />
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3">
                        <Metric label={dictionary.formArticleCount} value={String(item.total_entries)} />
                        <Metric label={dictionary.insertedArticles} value={String(item.inserted_entries)} />
                        <Metric
                          label={dictionary.deduplicatedArticles}
                          value={String(item.deduplicated_entries)}
                        />
                      </div>
                      {item.error_message ? (
                        <p className="mt-3 text-sm text-rose-700">{item.error_message}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {sources.length === 0 ? (
            <EmptyState title={dictionary.empty} description={dictionary.sourcesDescription} />
          ) : (
            sources.map((source) => {
              const rssReady = source.source_type === "rss" && !!source.rss_url;
              return (
                <article key={source.id} className="app-panel p-6 sm:p-7">
                  <div className="flex flex-col gap-5">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="max-w-3xl text-[32px] font-semibold tracking-[-0.05em] text-slate-950">
                            {source.name}
                          </h3>
                          <StatusBadge
                            label={source.is_active ? dictionary.active : dictionary.paused}
                            tone={source.is_active ? "success" : "warning"}
                          />
                          <StatusBadge label={labels.sourceTypeValue(source.source_type)} />
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
                          <span>
                            {dictionary.formFetchStatus}: {rssReady ? source.last_fetch_status : labels.unlinkedRss}
                          </span>
                          <span>
                            {dictionary.formLastFetched}: {formatDate(source.last_fetched_at, language)}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 xl:max-w-[460px] xl:justify-end">
                        <button
                          type="button"
                          onClick={() => startEdit(source)}
                          className="app-button-secondary"
                        >
                          {dictionary.edit}
                        </button>
                        {rssReady ? (
                          <>
                            <button
                              type="button"
                              onClick={() => void runAction(source, "test")}
                              className="app-button-secondary"
                            >
                              {labels.testRss}
                            </button>
                            <button
                              type="button"
                              onClick={() => void runAction(source, "fetch")}
                              className="app-button-secondary"
                            >
                              {dictionary.fetch}
                            </button>
                            <button
                              type="button"
                              onClick={() => void runAction(source, "sync")}
                              className="app-button-secondary"
                            >
                              {labels.syncFetch}
                            </button>
                          </>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => void runAction(source, "toggle")}
                          className="app-button-secondary"
                        >
                          {source.is_active ? labels.disableSource : labels.enableSource}
                        </button>
                        <button
                          type="button"
                          onClick={() => void removeSource(source)}
                          className="app-button-danger"
                        >
                          {dictionary.delete}
                        </button>
                      </div>
                    </div>

                    <div className="grid gap-3 lg:grid-cols-2">
                      <LinkCard
                        label="RSS"
                        value={source.rss_url || labels.unlinkedRss}
                        href={rssReady ? source.rss_url : null}
                      />
                      <LinkCard
                        label="Homepage"
                        value={source.homepage_url || "-"}
                        href={source.homepage_url}
                      />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                      <SourceMetric label={labels.sourceType} value={labels.sourceTypeValue(source.source_type)} />
                      <SourceMetric label={dictionary.formLanguage} value={source.language} />
                      <SourceMetric label={dictionary.formPriority} value={String(source.priority)} />
                      <SourceMetric label={dictionary.formArticleCount} value={String(source.article_count)} />
                      <SourceMetric
                        label={dictionary.formFetchStatus}
                        value={rssReady ? source.last_fetch_status : labels.manualOnly}
                      />
                    </div>

                    {!rssReady ? (
                      <p className="text-sm text-slate-500">{labels.noRssActions}</p>
                    ) : null}
                    {source.last_fetch_error ? (
                      <p className="text-sm text-rose-700">
                        {dictionary.formFetchError}: {source.last_fetch_error}
                      </p>
                    ) : null}
                  </div>
                </article>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}
