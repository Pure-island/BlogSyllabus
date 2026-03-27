"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArticleTitleLink } from "@/components/article-title-link";
import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { labelForDifficulty, labelForStage, labelForStatus } from "@/lib/i18n";
import type { WeeklyReview } from "@/lib/types";

function formatDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
}

function formatTopicLabel(topicKey: string | null) {
  if (!topicKey) return "Track";
  const normalized = topicKey.split(":").slice(1).join(":") || topicKey;
  return normalized
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function WeeklyPage() {
  const { dictionary, language, settings } = useI18n();
  const [currentReview, setCurrentReview] = useState<WeeklyReview | null>(null);
  const [history, setHistory] = useState<WeeklyReview[]>([]);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const providerReady =
    !!settings?.llm_enabled &&
    !!settings.llm_api_key.trim() &&
    !!settings.llm_model.trim();

  async function load() {
    const [current, items] = await Promise.all([
      api.getCurrentWeekly(),
      api.getWeeklyHistory(),
    ]);
    setCurrentReview(current);
    setHistory(items);
  }

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        await load();
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load weekly plan.");
      }
    })();
  }, []);

  const generate = async () => {
    try {
      setGenerating(true);
      setMessage(null);
      setError(null);
      setCurrentReview(await api.generateWeekly());
      await load();
      setMessage(dictionary.successGenerated);
    } catch (generateError) {
      setError(generateError instanceof ApiError ? generateError.message : "Generate failed.");
    } finally {
      setGenerating(false);
    }
  };

  const generationHint =
    language === "zh-CN"
      ? providerReady
        ? "已接入 provider，本周主线会先做规则分线，再由模型修正主题与顺序。"
        : "当前未配置 provider，本周计划会退回到规则分线与排序，不会阻塞生成。"
      : providerReady
        ? "The configured provider refines the weekly tracks after the rule-based pre-grouping step."
        : "No provider is configured, so this falls back to rule-based track grouping and ordering.";

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Weekly"
        title={dictionary.weeklyTitle}
        description={dictionary.weeklyDescription}
        action={
          <button
            type="button"
            onClick={() => void generate()}
            disabled={generating}
            className="app-button-primary disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {generating ? dictionary.loading : dictionary.generateWeekly}
          </button>
        }
      />

      <div className={`mb-4 app-alert ${providerReady ? "app-alert-success" : "app-alert-warn"}`}>
        {generationHint}{" "}
        {!providerReady ? (
          <Link className="font-semibold underline" href="/settings">
            {dictionary.settingsCta}
          </Link>
        ) : null}
      </div>
      {message ? <div className="app-alert app-alert-success mb-4">{message}</div> : null}
      {error ? <div className="app-alert app-alert-error mb-4">{error}</div> : null}

      {!currentReview && history.length === 0 ? (
        <EmptyState title={dictionary.noWeeklyPlan} description={dictionary.weeklyDescription} />
      ) : (
        <div className="space-y-6">
          {!currentReview ? null : (
            <div className="space-y-6">
              <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
                <div className="app-panel p-6">
                  <div className="text-sm font-semibold text-slate-950">
                    {formatDate(currentReview.week_start, language)}
                  </div>
                  {currentReview.generated_plan ? (
                    <div className="mt-4">
                      <h3 className="text-lg font-semibold text-slate-950">{dictionary.weeklyTitle}</h3>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">
                        {currentReview.generated_plan}
                      </p>
                    </div>
                  ) : null}
                  {currentReview.generated_review ? (
                    <div className="mt-6 border-t border-slate-200/80 pt-6">
                      <h3 className="text-lg font-semibold text-slate-950">{dictionary.reviewPrompt}</h3>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">
                        {currentReview.generated_review}
                      </p>
                    </div>
                  ) : null}
                </div>

                <div className="app-panel p-6">
                  <div className="app-section-head">
                    <p className="app-kicker">Tracks</p>
                    <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">
                      {language === "zh-CN" ? "本周选中的文章" : "Selected readings"}
                    </h3>
                  </div>
                  <div className="mt-4 space-y-4">
                    <TrackSummary
                      title={dictionary.primaryRead}
                      topicKey={currentReview.primary_topic_key}
                      count={currentReview.primary_articles.length}
                    />
                    <TrackSummary
                      title={dictionary.supplementalRead}
                      topicKey={currentReview.supplemental_topic_key}
                      count={currentReview.supplemental_articles.length}
                    />
                  </div>
                </div>
              </div>

              <div className="grid gap-6 xl:grid-cols-2">
                <WeeklyTrackPanel
                  title={dictionary.primaryRead}
                  items={currentReview.primary_articles}
                  language={language}
                />
                <WeeklyTrackPanel
                  title={dictionary.supplementalRead}
                  items={currentReview.supplemental_articles}
                  language={language}
                />
              </div>
            </div>
          )}

          <div className="app-panel p-6">
            <div className="app-section-head">
              <p className="app-kicker">Archive</p>
              <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">
                {dictionary.history}
              </h3>
            </div>
            <div className="mt-4 space-y-3">
              {history.length === 0 ? (
                <p className="text-sm text-slate-500">{dictionary.noWeeklyPlan}</p>
              ) : (
                history.map((item) => (
                  <div key={item.id} className="app-subcard px-4 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="font-medium text-slate-900">{formatDate(item.week_start, language)}</div>
                      {item.primary_topic_key ? (
                        <StatusBadge label={formatTopicLabel(item.primary_topic_key)} tone="success" />
                      ) : null}
                      {item.supplemental_topic_key ? (
                        <StatusBadge label={formatTopicLabel(item.supplemental_topic_key)} />
                      ) : null}
                    </div>
                    {item.generated_plan ? (
                      <p className="mt-2 line-clamp-3 text-sm leading-7 text-slate-600">{item.generated_plan}</p>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function TrackSummary({
  title,
  topicKey,
  count,
}: {
  title: string;
  topicKey: string | null;
  count: number;
}) {
  return (
    <div className="app-subcard p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">{title}</div>
      <div className="mt-2 text-lg font-semibold text-slate-950">{formatTopicLabel(topicKey)}</div>
      <div className="mt-1 text-sm text-slate-500">{count} items</div>
    </div>
  );
}

function WeeklyTrackPanel({
  title,
  items,
  language,
}: {
  title: string;
  items: WeeklyReview["primary_articles"];
  language: "zh-CN" | "en";
}) {
  return (
    <div className="app-panel p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="app-kicker">{title}</p>
          <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">
            {items[0]?.topic_key ? formatTopicLabel(items[0].topic_key) : title}
          </h3>
        </div>
        <StatusBadge label={`${items.length}`} tone="success" />
      </div>

      {items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">
          {language === "zh-CN" ? "本周没有选出这一条线。" : "No articles were selected for this track this week."}
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <article key={`${title}-${item.article.id}`} className="app-subcard p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge label={`#${item.sequence_rank}`} tone="success" />
                <StatusBadge label={labelForStatus(language, item.article.status)} />
                <StatusBadge label={labelForStage(language, item.article.stage)} tone="success" />
                <StatusBadge label={labelForDifficulty(language, item.article.difficulty)} tone="warning" />
              </div>
              <ArticleTitleLink
                title={item.article.title}
                url={item.article.url}
                className="mt-3 block text-lg font-semibold text-slate-950"
              />
              <p className="mt-2 text-sm text-slate-500">{item.article.source_name_snapshot}</p>
              {item.reason ? <p className="mt-3 text-sm leading-7 text-slate-600">{item.reason}</p> : null}
              {item.article.raw_summary ? (
                <p className="mt-2 text-sm leading-7 text-slate-500">{item.article.raw_summary}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
