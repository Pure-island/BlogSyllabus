"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArticleTitleLink } from "@/components/article-title-link";
import { useI18n } from "@/components/language-provider";
import { api } from "@/lib/api";
import type { ProgressResponse, TodayResponse } from "@/lib/types";

const quickLinks = [
  { href: "/sources", accent: "from-sky-500 to-cyan-400", key: "quickActionSources" },
  { href: "/curriculum", accent: "from-emerald-500 to-lime-400", key: "quickActionCurriculum" },
  { href: "/today", accent: "from-amber-500 to-orange-400", key: "quickActionToday" },
  { href: "/weekly", accent: "from-fuchsia-500 to-pink-400", key: "quickActionWeekly" },
  { href: "/settings", accent: "from-slate-700 to-slate-500", key: "quickActionSettings" },
] as const;

function formatDate(value: string | null, locale: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DashboardPage() {
  const { dictionary, language } = useI18n();
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [today, setToday] = useState<TodayResponse | null>(null);

  useEffect(() => {
    void Promise.allSettled([api.getProgress(), api.getToday()]).then((results) => {
      const [progressResult, todayResult] = results;
      if (progressResult.status === "fulfilled") {
        setProgress(progressResult.value);
      }
      if (todayResult.status === "fulfilled") {
        setToday(todayResult.value);
      }
    });
  }, []);

  const cards = [
    {
      label: dictionary.totalArticles,
      value: String(progress?.total_articles ?? 0),
    },
    {
      label: dictionary.completedArticles,
      value: String(progress?.completed_articles ?? 0),
    },
    {
      label: dictionary.inProgressArticles,
      value: String(progress?.in_progress_articles ?? 0),
    },
    {
      label: dictionary.generatedAt,
      value: today ? formatDate(today.generated_at, language) : "-",
    },
  ];

  return (
    <section className="pb-3 lg:h-[calc(100vh-2.5rem)]">
      <div className="grid h-full gap-5 lg:grid-rows-[auto_1fr]">
        <div className="surface-panel-strong rounded-[34px] p-5">
          <div className="mb-4 flex items-end justify-between gap-4 border-b border-slate-200/70 pb-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
                Overview
              </p>
              <h2 className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-slate-950">
                Dashboard
              </h2>
            </div>
            <p className="hidden max-w-xl text-sm leading-6 text-slate-500 xl:block">
              Sources, progress, and next actions in one screen.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map((card) => (
              <div
                key={card.label}
                className="rounded-[24px] border border-white/85 bg-white/90 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.045)]"
              >
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                  {card.label}
                </div>
                <div className="mt-2 text-[34px] font-semibold tracking-[-0.05em] text-slate-950">
                  {card.value}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid min-h-0 gap-5 xl:grid-cols-[1.05fr_1.15fr]">
          <SectionBlock
            eyebrow="Today"
            title={dictionary.todayTitle}
            description="The most relevant article to move forward right now."
            compact
          >
            <div className="rounded-[24px] border border-white/85 bg-white/90 p-5 shadow-[0_10px_24px_rgba(15,23,42,0.045)]">
                {today?.primary_article ? (
                  <ArticleTitleLink
                    title={today.primary_article.title}
                    url={today.primary_article.url}
                    className="text-[15px] leading-8 text-slate-500"
                  />
                ) : (
                  <p className="text-[15px] leading-8 text-slate-500">{dictionary.noTodayPlan}</p>
                )}
            </div>
          </SectionBlock>

          <div className="grid min-h-0 gap-5 lg:grid-rows-[auto_1fr]">
            <SectionBlock
              eyebrow="Shortcuts"
              title="Next step"
              description="Jump into the most common flows."
              compact
            >
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {quickLinks.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group overflow-hidden rounded-[24px] border border-white/85 bg-white/90 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.045)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_36px_rgba(15,23,42,0.07)]"
                  >
                    <div className={`h-1.5 w-14 rounded-full bg-gradient-to-r ${item.accent}`} />
                    <h3 className="mt-4 text-sm font-semibold tracking-[-0.03em] text-slate-950">
                      {dictionary[item.key]}
                    </h3>
                  </Link>
                ))}
              </div>
            </SectionBlock>

            <SectionBlock
              eyebrow="Signals"
              title={dictionary.progressTitle}
              description="A compact snapshot of your most visible progress signal."
              compact
            >
              <div className="rounded-[24px] border border-white/85 bg-white/90 p-5 shadow-[0_10px_24px_rgba(15,23,42,0.045)]">
                <p className="text-[15px] leading-8 text-slate-500">
                  {progress?.source_breakdown.length
                    ? `${progress.source_breakdown[0].source_name}: ${progress.source_breakdown[0].completed}/${progress.source_breakdown[0].total}`
                    : dictionary.noProgress}
                </p>
              </div>
            </SectionBlock>
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionBlock({
  eyebrow,
  title,
  description,
  children,
  compact = false,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div className="surface-panel-strong rounded-[34px] p-5 sm:p-6">
      <div className={`border-b border-slate-200/70 ${compact ? "mb-4 pb-3" : "mb-5 pb-4"}`}>
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
          {eyebrow}
        </p>
        <h3 className={`mt-2 font-semibold tracking-[-0.04em] text-slate-950 ${compact ? "text-[22px]" : "text-[28px]"}`}>
          {title}
        </h3>
        <p className={`mt-2 max-w-2xl text-slate-500 ${compact ? "text-sm leading-6" : "text-[15px] leading-7"}`}>
          {description}
        </p>
      </div>
      {children}
    </div>
  );
}
