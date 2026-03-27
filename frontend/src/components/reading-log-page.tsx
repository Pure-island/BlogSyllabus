"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ArticleTitleLink } from "@/components/article-title-link";
import { api, ApiError } from "@/lib/api";
import { labelForStatus } from "@/lib/i18n";
import type { Article, ReadingLog, ReadingLogPayload, ReadingStatus } from "@/lib/types";

const emptyLog: ReadingLogPayload = {
  article_id: 0,
  read_date: new Date().toISOString().slice(0, 10),
  status_after_read: "planned",
  one_sentence_summary: null,
  key_insight: null,
  open_question: null,
  next_action: null,
};

const availableStatuses: ReadingStatus[] = [
  "planned",
  "skimmed",
  "deep_read",
  "reviewed",
  "mastered",
];

export function ReadingLogPage() {
  const { dictionary, language } = useI18n();
  const [logs, setLogs] = useState<ReadingLog[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [form, setForm] = useState<ReadingLogPayload>(emptyLog);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        const [logList, articleList] = await Promise.all([
          api.listReadingLogs(),
          api.listArticles(),
        ]);
        setLogs(logList);
        setArticles(articleList);
        setForm((current) =>
          !current.article_id && articleList[0]
            ? { ...current, article_id: articleList[0].id }
            : current,
        );
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load reading logs.");
      }
    })();
  }, []);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await api.createReadingLog(form);
      setMessage(dictionary.successSaved);
      setForm({
        ...emptyLog,
        article_id: form.article_id,
      });
      const [logList, articleList] = await Promise.all([
        api.listReadingLogs(),
        api.listArticles(),
      ]);
      setLogs(logList);
      setArticles(articleList);
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Create failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="pb-8">
      <PageHeader eyebrow="Log" title={dictionary.logTitle} description={dictionary.logDescription} />

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <form onSubmit={submit} className="app-panel p-6 sm:p-7">
          <div className="app-section-head">
            <p className="app-kicker">Capture</p>
            <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">Session note</h3>
            <p className="app-copy mt-2">
              Record what changed in your understanding while the article is still fresh.
            </p>
          </div>
          <div className="grid gap-4">
            <label className="app-field">
              <span className="app-field-label">{dictionary.formArticle}</span>
              <select
                className="app-select"
                value={form.article_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, article_id: Number(event.target.value) }))
                }
              >
                {articles.map((article) => (
                  <option key={article.id} value={article.id}>
                    {article.title}
                  </option>
                ))}
              </select>
            </label>
            <TextField
              label={dictionary.formReadDate}
              value={form.read_date}
              onChange={(value) => setForm((current) => ({ ...current, read_date: value }))}
              type="date"
            />
            <label className="app-field">
              <span className="app-field-label">{dictionary.formStatus}</span>
              <select
                className="app-select"
                value={form.status_after_read}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    status_after_read: event.target.value as ReadingStatus,
                  }))
                }
              >
                {availableStatuses.map((status) => (
                  <option key={status} value={status}>
                    {labelForStatus(language, status)}
                  </option>
                ))}
              </select>
            </label>
            <TextField
              label={dictionary.formSummary}
              value={form.one_sentence_summary ?? ""}
              onChange={(value) =>
                setForm((current) => ({ ...current, one_sentence_summary: value || null }))
              }
              multiline
            />
            <TextField
              label={dictionary.formInsight}
              value={form.key_insight ?? ""}
              onChange={(value) =>
                setForm((current) => ({ ...current, key_insight: value || null }))
              }
              multiline
            />
            <TextField
              label={dictionary.formQuestion}
              value={form.open_question ?? ""}
              onChange={(value) =>
                setForm((current) => ({ ...current, open_question: value || null }))
              }
              multiline
            />
            <TextField
              label={dictionary.formNextAction}
              value={form.next_action ?? ""}
              onChange={(value) =>
                setForm((current) => ({ ...current, next_action: value || null }))
              }
              multiline
            />
          </div>

          <button
            type="submit"
            disabled={saving || !form.article_id}
            className="app-button-primary mt-6 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {saving ? dictionary.loading : dictionary.save}
          </button>
        </form>

        <div className="space-y-4">
          {message ? (
            <div className="app-alert app-alert-success">
              {message}
            </div>
          ) : null}
          {error ? (
            <div className="app-alert app-alert-error">
              {error}
            </div>
          ) : null}

          {logs.length === 0 ? (
            <EmptyState title={dictionary.noLogs} description={dictionary.logDescription} />
          ) : (
            logs.map((log) => (
              <article
                key={log.id}
                className="app-panel p-6"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {log.article_url ? (
                    <ArticleTitleLink
                      title={log.article_title}
                      url={log.article_url}
                      className="text-xl font-semibold text-slate-950"
                    />
                  ) : (
                    <h3 className="text-xl font-semibold text-slate-950">{log.article_title}</h3>
                  )}
                  <StatusBadge label={labelForStatus(language, log.status_after_read)} />
                </div>
                <p className="mt-2 text-sm text-slate-500">{log.read_date}</p>
                {log.one_sentence_summary ? (
                  <p className="mt-4 text-sm leading-7 text-slate-600">{log.one_sentence_summary}</p>
                ) : null}
                {log.key_insight ? (
                  <p className="mt-3 text-sm text-slate-700">
                    <strong>{dictionary.formInsight}: </strong>
                    {log.key_insight}
                  </p>
                ) : null}
                {log.open_question ? (
                  <p className="mt-2 text-sm text-slate-700">
                    <strong>{dictionary.formQuestion}: </strong>
                    {log.open_question}
                  </p>
                ) : null}
                {log.next_action ? (
                  <p className="mt-2 text-sm text-slate-700">
                    <strong>{dictionary.formNextAction}: </strong>
                    {log.next_action}
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
  type = "text",
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  multiline?: boolean;
}) {
  return (
    <label className="app-field">
      <span className="app-field-label">{label}</span>
      {multiline ? (
        <textarea
          className="app-textarea"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <input
          type={type}
          className="app-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </label>
  );
}
