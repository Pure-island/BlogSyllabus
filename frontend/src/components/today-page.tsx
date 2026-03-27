"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ArticleTitleLink } from "@/components/article-title-link";
import { api, ApiError } from "@/lib/api";
import { labelForDifficulty, labelForStage, labelForStatus } from "@/lib/i18n";
import type { Article, ReadingStatus, TodayResponse } from "@/lib/types";

const statusFlow: ReadingStatus[] = [
  "planned",
  "skimmed",
  "deep_read",
  "reviewed",
  "mastered",
];

function formatDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function TodayPage() {
  const { dictionary, language } = useI18n();
  const [today, setToday] = useState<TodayResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setToday(await api.getToday());
  }

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        await load();
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load today.");
      }
    })();
  }, []);

  const updateStatus = async (article: Article, status: ReadingStatus) => {
    try {
      setError(null);
      setMessage(null);
      await api.updateArticle(article.id, { status });
      setMessage(dictionary.successSaved);
      await load();
    } catch (updateError) {
      setError(updateError instanceof ApiError ? updateError.message : "Update failed.");
    }
  };

  const regenerate = async () => {
    try {
      setError(null);
      setMessage(null);
      setToday(await api.generateToday());
      setMessage(dictionary.successGenerated);
    } catch (updateError) {
      setError(updateError instanceof ApiError ? updateError.message : "Generate failed.");
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Today"
        title={dictionary.todayTitle}
        description={dictionary.todayDescription}
        action={
          <button
            type="button"
            onClick={() => void regenerate()}
            className="app-button-primary"
          >
            {dictionary.regenerateToday}
          </button>
        }
      />

      {message ? (
        <div className="app-alert app-alert-success mb-4">
          {message}
        </div>
      ) : null}
      {error ? (
        <div className="app-alert app-alert-error mb-4">
          {error}
        </div>
      ) : null}

      {!today || (!today.primary_article && !today.secondary_article) ? (
        <EmptyState title={dictionary.noTodayPlan} description={dictionary.todayDescription} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric label={dictionary.generatedAt} value={today ? formatDate(today.generated_at, language) : "-"} />
            <Metric label={dictionary.candidateCount} value={String(today?.candidate_count ?? 0)} />
            <Metric label={dictionary.primaryRead} value={today?.primary_article ? dictionary.yes : dictionary.no} />
            <Metric label={dictionary.supplementalRead} value={today?.secondary_article ? dictionary.yes : dictionary.no} />
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <ArticlePanel
              title={dictionary.primaryRead}
              article={today.primary_article}
              language={language}
              dictionary={dictionary}
              onStatusChange={updateStatus}
            />
            <ArticlePanel
              title={dictionary.supplementalRead}
              article={today.secondary_article}
              language={language}
              dictionary={dictionary}
              onStatusChange={updateStatus}
            />
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-stat p-5">
      <div className="app-stat-label">{label}</div>
      <div className="mt-2 text-[30px] font-semibold tracking-[-0.04em] text-slate-950">{value}</div>
    </div>
  );
}

function ArticlePanel({
  title,
  article,
  language,
  dictionary,
  onStatusChange,
}: {
  title: string;
  article: Article | null;
  language: "zh-CN" | "en";
  dictionary: ReturnType<typeof useI18n>["dictionary"];
  onStatusChange: (article: Article, status: ReadingStatus) => Promise<void>;
}) {
  if (!article) {
    return (
      <div className="app-panel p-6">
        <div className="text-lg font-semibold text-slate-950">{title}</div>
        <p className="mt-3 text-sm text-slate-500">{dictionary.noTodayPlan}</p>
      </div>
    );
  }

  return (
    <article className="app-panel p-6">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-lg font-semibold text-slate-950">{title}</div>
        <StatusBadge label={labelForStatus(language, article.status)} />
        <StatusBadge label={labelForStage(language, article.stage)} tone="success" />
        <StatusBadge label={labelForDifficulty(language, article.difficulty)} tone="warning" />
      </div>
      <ArticleTitleLink
        title={article.title}
        url={article.url}
        className="mt-4 block text-2xl font-semibold text-slate-950"
      />
      <p className="mt-2 text-sm text-slate-600">{article.source_name_snapshot || dictionary.sourceUnknown}</p>
      {article.raw_summary ? (
        <p className="mt-4 text-sm leading-7 text-slate-600">{article.raw_summary}</p>
      ) : null}
      <a
        className="mt-4 inline-flex text-sm font-semibold text-sky-700 hover:text-sky-900"
        href={article.url}
        target="_blank"
        rel="noreferrer"
      >
        {dictionary.open}
      </a>

      <div className="mt-6 flex flex-wrap gap-2">
        {statusFlow.map((status) => (
          <button
            key={`${article.id}-${status}`}
            type="button"
            onClick={() => void onStatusChange(article, status)}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              article.status === status
                ? "pill-primary text-white"
                : "app-button-secondary text-slate-700"
            }`}
          >
            {labelForStatus(language, status)}
          </button>
        ))}
      </div>
    </article>
  );
}
