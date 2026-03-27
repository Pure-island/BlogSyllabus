"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { api, ApiError } from "@/lib/api";
import { labelForStage, labelForStatus } from "@/lib/i18n";
import type { ProgressBucket, ProgressResponse } from "@/lib/types";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-stat p-5">
      <div className="app-stat-label">{label}</div>
      <div className="app-stat-value mt-2">{value}</div>
    </div>
  );
}

function Breakdown({
  title,
  items,
}: {
  title: string;
  items: ProgressBucket[];
}) {
  return (
    <div className="app-panel p-6">
      <div className="app-section-head">
        <p className="app-kicker">Breakdown</p>
        <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">{title}</h3>
      </div>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">-</p>
        ) : (
          items.map((item) => (
            <div key={`${title}-${item.label}`} className="app-subcard flex items-center justify-between gap-3 px-4 py-3">
              <span className="text-sm text-slate-700">{item.label}</span>
              <span className="text-sm font-semibold text-slate-950">{item.count}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function ProgressPage() {
  const { dictionary, language } = useI18n();
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        setProgress(await api.getProgress());
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load progress.");
      }
    })();
  }, []);

  const stageBreakdown =
    progress?.stage_breakdown.map((item) => ({
      ...item,
      label:
        item.label === "unassigned"
          ? "Unassigned"
          : labelForStage(language, item.label as Parameters<typeof labelForStage>[1]),
    })) ?? [];

  const statusBreakdown =
    progress?.status_breakdown.map((item) => ({
      ...item,
      label: labelForStatus(language, item.label as Parameters<typeof labelForStatus>[1]),
    })) ?? [];

  const tagBreakdown = progress?.tag_breakdown ?? [];

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Progress"
        title={dictionary.progressTitle}
        description={dictionary.progressDescription}
      />

      {error ? (
        <div className="app-alert app-alert-error mb-4">
          {error}
        </div>
      ) : null}

      {!progress || progress.total_articles === 0 ? (
        <EmptyState title={dictionary.noProgress} description={dictionary.progressDescription} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Metric label={dictionary.totalArticles} value={String(progress.total_articles)} />
            <Metric label={dictionary.completedArticles} value={String(progress.completed_articles)} />
            <Metric label={dictionary.inProgressArticles} value={String(progress.in_progress_articles)} />
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <Breakdown title={dictionary.formStage} items={stageBreakdown} />
            <Breakdown title={dictionary.formStatus} items={statusBreakdown} />
            <Breakdown title={dictionary.formTags} items={tagBreakdown} />
          </div>

          <div className="app-panel p-6">
            <div className="app-section-head">
              <p className="app-kicker">Sources</p>
              <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">{dictionary.articleSource}</h3>
            </div>
            <div className="mt-4 space-y-3">
              {progress.source_breakdown.map((source) => (
                <div
                  key={`${source.source_id ?? "unknown"}-${source.source_name}`}
                  className="app-subcard grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1fr)_120px_120px_120px]"
                >
                  <div className="font-medium text-slate-900">{source.source_name}</div>
                  <div className="text-sm text-slate-600">{dictionary.totalArticles}: {source.total}</div>
                  <div className="text-sm text-slate-600">{dictionary.completedArticles}: {source.completed}</div>
                  <div className="text-sm text-slate-600">{dictionary.inProgressArticles}: {source.in_progress}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
