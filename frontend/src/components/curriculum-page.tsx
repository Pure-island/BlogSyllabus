"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ArticleTitleLink } from "@/components/article-title-link";
import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { labelForDifficulty, labelForStage, labelForStatus } from "@/lib/i18n";
import type { Article, CurriculumResponse, DifficultyLevel, LanguageCode, ReadingStage, ReadingStatus } from "@/lib/types";

const stageOrder: Array<keyof CurriculumResponse> = ["foundation", "core", "frontier", "update", "unassigned"];

function parseTags(raw: string) {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function stageOptions(): Array<ReadingStage | ""> {
  return ["", "foundation", "core", "frontier", "update"];
}

function difficultyOptions(): Array<DifficultyLevel | ""> {
  return ["", "beginner", "intermediate", "advanced"];
}

function statusOptions(): Array<ReadingStatus | ""> {
  return ["", "planned", "skimmed", "deep_read", "reviewed", "mastered"];
}

function stageTitle(language: LanguageCode, stageKey: keyof CurriculumResponse) {
  return stageKey === "unassigned" ? (language === "zh-CN" ? "未分配" : "Unassigned") : labelForStage(language, stageKey);
}

export function CurriculumPage() {
  const { dictionary, language, settings } = useI18n();
  const [curriculum, setCurriculum] = useState<CurriculumResponse | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<ReadingStatus | "">("");
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyLevel | "">("");
  const [coreOnly, setCoreOnly] = useState(false);
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({
    foundation: true,
    core: true,
    frontier: false,
    update: false,
    unassigned: false,
  });
  const [expandedArticles, setExpandedArticles] = useState<Record<number, boolean>>({});

  const providerReady =
    !!settings?.llm_enabled &&
    !!settings.llm_api_key.trim() &&
    !!settings.llm_model.trim();

  async function loadCurriculum() {
    setCurriculum(await api.getCurriculum());
  }

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        await loadCurriculum();
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load curriculum.");
      }
    })();
  }, []);

  const allArticles = useMemo(
    () => (curriculum ? stageOrder.flatMap((key) => curriculum[key]) : []),
    [curriculum],
  );

  const sourceOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const article of allArticles) {
      const name = article.source_name_snapshot || dictionary.sourceUnknown;
      seen.set(name, name);
    }
    return Array.from(seen.values()).sort((a, b) => a.localeCompare(b));
  }, [allArticles, dictionary.sourceUnknown]);

  const filteredCurriculum = useMemo(() => {
    if (!curriculum) return null;

    const normalizedQuery = query.trim().toLowerCase();

    const matches = (article: Article) => {
      if (normalizedQuery) {
        const haystack = [
          article.title,
          article.source_name_snapshot || "",
          article.raw_summary || "",
          article.tags.join(" "),
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(normalizedQuery)) return false;
      }
      if (sourceFilter && (article.source_name_snapshot || dictionary.sourceUnknown) !== sourceFilter) {
        return false;
      }
      if (statusFilter && article.status !== statusFilter) {
        return false;
      }
      if (difficultyFilter && article.difficulty !== difficultyFilter) {
        return false;
      }
      if (coreOnly && !article.is_core) {
        return false;
      }
      return true;
    };

    return stageOrder.reduce(
      (acc, key) => {
        acc[key] = curriculum[key].filter(matches);
        return acc;
      },
      {
        foundation: [],
        core: [],
        frontier: [],
        update: [],
        unassigned: [],
      } as CurriculumResponse,
    );
  }, [coreOnly, curriculum, dictionary.sourceUnknown, difficultyFilter, query, sourceFilter, statusFilter]);

  const totalArticles = allArticles.length;
  const filteredTotal = filteredCurriculum
    ? stageOrder.reduce((sum, key) => sum + filteredCurriculum[key].length, 0)
    : 0;

  const handleUpdate = async (article: Article, patch: Partial<Article>) => {
    try {
      setSavingId(article.id);
      setError(null);
      setMessage(null);
      await api.updateArticle(article.id, {
        stage: patch.stage ?? article.stage,
        difficulty: patch.difficulty ?? article.difficulty,
        is_core: patch.is_core ?? article.is_core,
        tags: patch.tags ?? article.tags,
        estimated_minutes: patch.estimated_minutes ?? article.estimated_minutes,
      });
      setMessage(dictionary.successSaved);
      await loadCurriculum();
    } catch (updateError) {
      setError(updateError instanceof ApiError ? updateError.message : "Update failed.");
    } finally {
      setSavingId(null);
    }
  };

  const handleAnalyze = async (articleId: number) => {
    try {
      setAnalyzingId(articleId);
      setError(null);
      setMessage(null);
      await api.analyzeArticle(articleId);
      setMessage(dictionary.successGenerated);
      await loadCurriculum();
    } catch (analyzeError) {
      setError(analyzeError instanceof ApiError ? analyzeError.message : "Analyze failed.");
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleAnalyzeBatch = async () => {
    try {
      setError(null);
      setMessage(null);
      const result = await api.analyzeBatch();
      setMessage(result.message);
    } catch (analyzeError) {
      setError(analyzeError instanceof ApiError ? analyzeError.message : "Analyze failed.");
    }
  };

  const toggleStage = (stageKey: keyof CurriculumResponse) => {
    setExpandedStages((current) => ({ ...current, [stageKey]: !current[stageKey] }));
  };

  const toggleArticle = (articleId: number) => {
    setExpandedArticles((current) => ({ ...current, [articleId]: !current[articleId] }));
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Curriculum"
        title={dictionary.curriculumTitle}
        description={dictionary.curriculumDescription}
        action={
          <button
            type="button"
            onClick={() => void handleAnalyzeBatch()}
            disabled={!providerReady}
            className="app-button-primary disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {dictionary.analyzeBatch}
          </button>
        }
      />

      {!providerReady ? (
        <div className="app-alert app-alert-warn mb-4">
          {dictionary.llmNotConfigured}{" "}
          <Link className="font-semibold underline" href="/settings">
            {dictionary.settingsCta}
          </Link>
        </div>
      ) : null}

      {message ? <div className="app-alert app-alert-success mb-4">{message}</div> : null}
      {error ? <div className="app-alert app-alert-error mb-4">{error}</div> : null}

      <div className="mb-4 grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <div className="app-panel p-6">
          <div className="app-section-head">
            <p className="app-kicker">{language === "zh-CN" ? "Overview" : "Overview"}</p>
            <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950">
              {language === "zh-CN" ? "课程概览" : "Curriculum overview"}
            </h3>
          </div>
          <div className="grid gap-3">
            <MetricCard label={dictionary.totalArticles} value={String(totalArticles)} />
            <MetricCard label={language === "zh-CN" ? "当前结果" : "Filtered"} value={String(filteredTotal)} />
            <MetricCard label={language === "zh-CN" ? "主干文章" : "Core only"} value={String(allArticles.filter((item) => item.is_core).length)} />
          </div>
        </div>

        <div className="app-panel p-6">
          <div className="app-section-head">
            <p className="app-kicker">{language === "zh-CN" ? "Browse" : "Browse"}</p>
            <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950">
              {language === "zh-CN" ? "快速筛选" : "Quick filters"}
            </h3>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <label className="app-field xl:col-span-2">
              <span className="app-field-label">{language === "zh-CN" ? "搜索文章" : "Search"}</span>
              <input
                className="app-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={language === "zh-CN" ? "按标题、来源、标签搜索" : "Search title, source, or tags"}
              />
            </label>
            <label className="app-field">
              <span className="app-field-label">{dictionary.filterBySource}</span>
              <select className="app-select" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
                <option value="">{dictionary.all}</option>
                {sourceOptions.map((sourceName) => (
                  <option key={sourceName} value={sourceName}>
                    {sourceName}
                  </option>
                ))}
              </select>
            </label>
            <label className="app-field">
              <span className="app-field-label">{dictionary.filterByStatus}</span>
              <select className="app-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReadingStatus | "")}>
                {statusOptions().map((option) => (
                  <option key={`status-${option || "all"}`} value={option}>
                    {option ? labelForStatus(language, option) : dictionary.all}
                  </option>
                ))}
              </select>
            </label>
            <label className="app-field">
              <span className="app-field-label">{dictionary.filterByDifficulty}</span>
              <select className="app-select" value={difficultyFilter} onChange={(event) => setDifficultyFilter(event.target.value as DifficultyLevel | "")}>
                {difficultyOptions().map((option) => (
                  <option key={`difficulty-${option || "all"}`} value={option}>
                    {option ? labelForDifficulty(language, option) : dictionary.all}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <label className="app-toggle">
              <input type="checkbox" checked={coreOnly} onChange={(event) => setCoreOnly(event.target.checked)} />
              {language === "zh-CN" ? "只看主干文章" : "Core only"}
            </label>
            <button
              type="button"
              className="app-button-secondary"
              onClick={() => {
                setQuery("");
                setSourceFilter("");
                setStatusFilter("");
                setDifficultyFilter("");
                setCoreOnly(false);
              }}
            >
              {language === "zh-CN" ? "清空筛选" : "Clear filters"}
            </button>
          </div>
        </div>
      </div>

      {totalArticles === 0 || !filteredCurriculum ? (
        <EmptyState title={dictionary.noCurriculum} description={dictionary.curriculumDescription} />
      ) : filteredTotal === 0 ? (
        <EmptyState
          title={language === "zh-CN" ? "没有匹配结果" : "No matching articles"}
          description={language === "zh-CN" ? "试试放宽筛选条件。" : "Try broadening your filters."}
        />
      ) : (
        <div className="space-y-5">
          {stageOrder.map((stageKey) => {
            const items = filteredCurriculum[stageKey];
            const expanded = expandedStages[stageKey];
            return (
              <section key={stageKey} className="app-panel overflow-hidden p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-xl font-semibold text-slate-950">{stageTitle(language, stageKey)}</h3>
                      <StatusBadge label={`${items.length}`} tone="neutral" />
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      {language === "zh-CN" ? "点击展开查看这个阶段的文章。" : "Expand to browse the articles in this stage."}
                    </p>
                  </div>
                  <button type="button" className="app-button-secondary" onClick={() => toggleStage(stageKey)}>
                    {expanded
                      ? language === "zh-CN"
                        ? "收起"
                        : "Collapse"
                      : language === "zh-CN"
                        ? "展开"
                        : "Expand"}
                  </button>
                </div>

                {expanded ? (
                  <div className="mt-5 space-y-4">
                    {items.length === 0 ? (
                      <p className="text-sm text-slate-500">{dictionary.empty}</p>
                    ) : (
                      items.map((article) => {
                        const articleExpanded = !!expandedArticles[article.id];
                        return (
                          <article key={article.id} className="app-subcard p-5">
                            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <ArticleTitleLink
                                    title={article.title}
                                    url={article.url}
                                    className="text-lg font-semibold text-slate-950"
                                  />
                                  <StatusBadge label={labelForStatus(language, article.status)} />
                                  <StatusBadge label={labelForDifficulty(language, article.difficulty)} tone="warning" />
                                  <StatusBadge
                                    label={article.stage ? labelForStage(language, article.stage) : stageTitle(language, "unassigned")}
                                    tone={article.stage ? "success" : "neutral"}
                                  />
                                  {article.is_core ? <StatusBadge label={language === "zh-CN" ? "主干" : "Core"} tone="success" /> : null}
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-600">
                                  <span>{article.source_name_snapshot || dictionary.sourceUnknown}</span>
                                  {article.estimated_minutes ? (
                                    <span>
                                      {language === "zh-CN" ? "预估" : "Est."} {article.estimated_minutes} min
                                    </span>
                                  ) : null}
                                  <span>
                                    {language === "zh-CN" ? "标签" : "Tags"}:{" "}
                                    {article.tags.length ? article.tags.slice(0, 4).join(", ") : "-"}
                                  </span>
                                </div>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  onClick={() => toggleArticle(article.id)}
                                  className="app-button-secondary"
                                >
                                  {articleExpanded
                                    ? language === "zh-CN"
                                      ? "收起详情"
                                      : "Hide details"
                                    : language === "zh-CN"
                                      ? "查看详情"
                                      : "Show details"}
                                </button>
                                <button
                                  type="button"
                                  disabled={!providerReady || analyzingId === article.id}
                                  onClick={() => void handleAnalyze(article.id)}
                                  className="app-button-secondary disabled:cursor-not-allowed disabled:bg-slate-200"
                                >
                                  {analyzingId === article.id ? dictionary.loading : dictionary.analyze}
                                </button>
                              </div>
                            </div>

                            {articleExpanded ? (
                              <div className="mt-5 border-t border-slate-200/70 pt-5">
                                {article.raw_summary ? (
                                  <p className="mb-4 text-sm leading-7 text-slate-600">{article.raw_summary}</p>
                                ) : null}
                                {article.tags.length ? (
                                  <div className="mb-4 flex flex-wrap gap-2">
                                    {article.tags.map((tag) => (
                                      <StatusBadge key={`${article.id}-${tag}`} label={tag} />
                                    ))}
                                  </div>
                                ) : null}

                                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                                  <label className="app-field">
                                    <span className="app-field-label">{dictionary.formStage}</span>
                                    <select
                                      className="app-select"
                                      value={article.stage ?? ""}
                                      onChange={(event) =>
                                        void handleUpdate(article, {
                                          stage: (event.target.value || null) as Article["stage"],
                                        })
                                      }
                                    >
                                      {stageOptions().map((option) => (
                                        <option key={`stage-${article.id}-${option || "none"}`} value={option}>
                                          {option ? labelForStage(language, option) : dictionary.all}
                                        </option>
                                      ))}
                                    </select>
                                  </label>

                                  <label className="app-field">
                                    <span className="app-field-label">{dictionary.formDifficulty}</span>
                                    <select
                                      className="app-select"
                                      value={article.difficulty ?? ""}
                                      onChange={(event) =>
                                        void handleUpdate(article, {
                                          difficulty: (event.target.value || null) as Article["difficulty"],
                                        })
                                      }
                                    >
                                      {difficultyOptions().map((option) => (
                                        <option key={`difficulty-${article.id}-${option || "none"}`} value={option}>
                                          {option ? labelForDifficulty(language, option) : dictionary.all}
                                        </option>
                                      ))}
                                    </select>
                                  </label>

                                  <label className="app-field xl:col-span-2">
                                    <span className="app-field-label">{dictionary.formTags}</span>
                                    <input
                                      className="app-input"
                                      defaultValue={article.tags.join(", ")}
                                      onBlur={(event) =>
                                        void handleUpdate(article, {
                                          tags: parseTags(event.target.value),
                                        })
                                      }
                                    />
                                  </label>
                                </div>

                                <div className="mt-3 flex flex-wrap gap-3">
                                  <label className="app-toggle">
                                    <input
                                      type="checkbox"
                                      checked={article.is_core}
                                      onChange={(event) => void handleUpdate(article, { is_core: event.target.checked })}
                                    />
                                    {dictionary.formCore}
                                  </label>
                                </div>

                                {savingId === article.id ? (
                                  <p className="mt-3 text-sm text-slate-500">{dictionary.loading}</p>
                                ) : null}
                              </div>
                            ) : null}
                          </article>
                        );
                      })
                    )}
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="app-subcard px-4 py-4">
      <div className="app-stat-label">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-slate-950">{value}</div>
    </div>
  );
}
