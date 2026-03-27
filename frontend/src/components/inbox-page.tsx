"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ArticleTitleLink } from "@/components/article-title-link";
import { EmptyState } from "@/components/empty-state";
import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { labelForDifficulty, labelForStage, labelForStatus } from "@/lib/i18n";
import type { Article, ArticleImportBatchResponse, ArticleImportPreviewResponse, ArticlePayload, ManualSourceDraft, Source } from "@/lib/types";

const emptyArticle: ArticlePayload = { title: "", url: "", source_id: null, source_name_snapshot: null, published_at: null, author: null, raw_summary: null, content_excerpt: null, difficulty: null, stage: null, estimated_minutes: null, status: "planned", is_core: false, core_score: null, core_reason: null, checkpoint_questions: [], tags: [] };
const emptyManualSource: ManualSourceDraft = { name: "", homepage_url: null, language: "zh-CN", priority: 50, is_active: true };
const examples = {
  titleUrl: "Understanding Agents https://example.com/understanding-agents",
  markdown: "[Planning in LLM Agents](https://example.com/planning-in-llm-agents)",
  urlOnly: "https://example.com/retrieval-augmented-generation",
  csv: "title,url,author,published_at\nAgent Survey,https://example.com/agent-survey,Alice,2026-03-01",
};
type BindingMode = "none" | "existing" | "new";

export function InboxPage() {
  const { dictionary, language, settings } = useI18n();
  const [articles, setArticles] = useState<Article[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [filters, setFilters] = useState({ source_id: "", status: "", difficulty: "" });
  const [form, setForm] = useState<ArticlePayload>(emptyArticle);
  const [saving, setSaving] = useState(false);
  const [rawImportText, setRawImportText] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [useLlmFallback, setUseLlmFallback] = useState(false);
  const [analyzeAfterImport, setAnalyzeAfterImport] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState<ArticleImportPreviewResponse | null>(null);
  const [bindingMode, setBindingMode] = useState<BindingMode>("none");
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [manualSourceDraft, setManualSourceDraft] = useState<ManualSourceDraft>(emptyManualSource);

  const providerReady = !!settings?.llm_enabled && !!settings.llm_api_key.trim() && !!settings.llm_model.trim();
  const t = useMemo(
    () =>
      language === "zh-CN"
        ? {
            importTitle: "批量文本导入", importDesc: "上传或粘贴文章列表，先预览，再导入。", file: "读取文件", raw: "原始文本", fileHint: "支持 .txt、.md、.csv，也支持直接粘贴标题 + 链接列表。", fileLoaded: "已载入文件",
            fallback: "规则解析失败时用大模型兜底", providerHint: "未配置可用 Provider 时，仍可导入，但无法使用兜底解析和自动分析。", preview: "解析预览", previewTitle: "导入预览",
            parsed: "可导入文章", dup: "重复文章", invalid: "无效行", usedLlm: "这次预览使用了大模型兜底解析。", binding: "来源归属", noBinding: "不关联来源", existing: "绑定到已有来源", manual: "新建手动来源",
            analyze: "导入后立即分析新文章", importNow: "确认导入", missingText: "请先输入要解析的文本。", previewFirst: "先输入内容并生成预览。", formats: "支持的文本格式", csvHint: "CSV 表头推荐使用 `title,url,author,published_at`。", formatOneTitle: "1. 标题 + URL", formatTwoTitle: "2. Markdown 链接", formatThreeTitle: "3. 每行一个 URL", formatFourTitle: "4. CSV 文件",
            createHint: "这个手动来源之后可以补填 RSS URL，升级为可订阅更新的来源。", bindingHint: "导入后也可以在来源页继续补填 RSS URL。", readFailed: "读取文件失败。",
            importResult: (r: ArticleImportBatchResponse) => `已导入 ${r.inserted_count} 篇，重复 ${r.duplicate_count} 篇，跳过 ${r.skipped_count} 条。`,
            previewCount: (n: number) => `共 ${n} 条`,
          }
        : {
            importTitle: "Batch text import", importDesc: "Upload or paste an article list, preview it, then import.", file: "Load file", raw: "Raw text", fileHint: "Supports .txt, .md, .csv, or pasted title + URL lists.", fileLoaded: "Loaded file",
            fallback: "Use LLM fallback if rule parsing misses items", providerHint: "Without a configured provider, import still works but LLM fallback and auto-analysis stay unavailable.", preview: "Preview import", previewTitle: "Import preview",
            parsed: "Importable articles", dup: "Duplicate articles", invalid: "Invalid lines", usedLlm: "LLM fallback was used for this preview.", binding: "Source binding", noBinding: "Do not link to a source", existing: "Link to an existing source", manual: "Create a new manual source",
            analyze: "Analyze new articles immediately after import", importNow: "Import now", missingText: "Please enter text to preview first.", previewFirst: "Add text or load a file to preview items first.", formats: "Supported formats", csvHint: "Recommended CSV headers: `title,url,author,published_at`.", formatOneTitle: "1. Title + URL", formatTwoTitle: "2. Markdown links", formatThreeTitle: "3. One URL per line", formatFourTitle: "4. CSV file",
            createHint: "You can add an RSS URL later to upgrade this manual source into a subscribable source.", bindingHint: "You can still add an RSS URL later from the source page.", readFailed: "Failed to read the selected file.",
            importResult: (r: ArticleImportBatchResponse) => `Imported ${r.inserted_count}, duplicated ${r.duplicate_count}, skipped ${r.skipped_count}.`,
            previewCount: (n: number) => `${n} items`,
          },
    [language],
  );

  const loadInbox = useCallback(async () => {
    const params = new URLSearchParams();
    if (filters.source_id) params.set("source_id", filters.source_id);
    if (filters.status) params.set("status", filters.status);
    if (filters.difficulty) params.set("difficulty", filters.difficulty);
    const [sourceList, inbox] = await Promise.all([api.listSources(), api.listInbox(params)]);
    setSources(sourceList);
    setArticles(inbox);
  }, [filters.difficulty, filters.source_id, filters.status]);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        await loadInbox();
      } catch (fetchError) {
        setError(fetchError instanceof ApiError ? fetchError.message : "Failed to load inbox.");
      }
    })();
  }, [loadInbox]);

  const sourceLookup = useMemo(() => new Map(sources.map((source) => [source.id, source.name])), [sources]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await api.createArticle(form);
      setMessage(dictionary.successSaved);
      setForm(emptyArticle);
      await loadInbox();
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Create failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setRawImportText(text);
      setSelectedFileName(file.name);
      setPreview(null);
      setMessage(null);
      setError(null);
    } catch {
      setError(t.readFailed);
    } finally {
      event.target.value = "";
    }
  };

  const previewImport = async () => {
    if (!rawImportText.trim()) {
      setError(t.missingText);
      setMessage(null);
      return;
    }
    setPreviewing(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.previewArticleImport({ raw_text: rawImportText, use_llm_fallback: providerReady && useLlmFallback });
      setPreview(result);
      if (!result.importable_count && !result.duplicate_count && !result.invalid_count) setMessage(dictionary.empty);
    } catch (previewError) {
      setError(previewError instanceof ApiError ? previewError.message : "Preview failed.");
    } finally {
      setPreviewing(false);
    }
  };

  const importPreview = async () => {
    if (!preview || preview.parsed_items.length === 0) {
      setError(t.previewFirst);
      setMessage(null);
      return;
    }
    setImporting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.importArticleBatch({
        items: preview.parsed_items,
        source_id: bindingMode === "existing" && selectedSourceId ? Number(selectedSourceId) : null,
        new_source: bindingMode === "new" ? manualSourceDraft : null,
        analyze_after_import: providerReady && analyzeAfterImport,
      });
      setMessage(t.importResult(result));
      setPreview(null);
      setRawImportText("");
      setSelectedFileName(null);
      setUseLlmFallback(false);
      setAnalyzeAfterImport(false);
      setBindingMode("none");
      setSelectedSourceId("");
      setManualSourceDraft(emptyManualSource);
      await loadInbox();
    } catch (importError) {
      setError(importError instanceof ApiError ? importError.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <section className="pb-8">
      <PageHeader eyebrow="Inbox" title={dictionary.inboxTitle} description={dictionary.inboxDescription} />
      <div className="grid gap-6 2xl:grid-cols-[360px_minmax(0,1fr)]">
        <form onSubmit={submit} className="app-panel p-6 sm:p-7">
          <div className="app-section-head">
            <p className="app-kicker">Capture</p>
            <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{dictionary.manualArticle}</h3>
            <p className="app-copy mt-2">{dictionary.inboxDescription}</p>
          </div>
          <div className="space-y-4">
            <TextField label={dictionary.articleTitle} value={form.title} onChange={(value) => setForm((current) => ({ ...current, title: value }))} required />
            <TextField label={dictionary.articleUrl} value={form.url} onChange={(value) => setForm((current) => ({ ...current, url: value }))} required />
            <label className="app-field">
              <span className="app-field-label">{dictionary.articleSource}</span>
              <select className="app-select" value={form.source_id ?? ""} onChange={(event) => setForm((current) => ({ ...current, source_id: event.target.value ? Number(event.target.value) : null }))}>
                <option value="">{dictionary.sourceUnknown}</option>
                {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
              </select>
            </label>
            <TextField label={dictionary.articleAuthor} value={form.author ?? ""} onChange={(value) => setForm((current) => ({ ...current, author: value || null }))} />
            <TextField label={dictionary.articleSummary} value={form.raw_summary ?? ""} onChange={(value) => setForm((current) => ({ ...current, raw_summary: value || null, content_excerpt: value || null }))} multiline />
          </div>
          <button type="submit" disabled={saving} className="app-button-primary mt-6 disabled:cursor-not-allowed disabled:bg-slate-400">
            {saving ? dictionary.loading : dictionary.save}
          </button>
        </form>

        <div className="space-y-4">
          {message ? <div className="app-alert app-alert-success">{message}</div> : null}
          {error ? <div className="app-alert app-alert-error">{error}</div> : null}

          <div className="app-panel p-6 sm:p-7">
            <div className="app-section-head">
              <p className="app-kicker">Bulk Import</p>
              <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{t.importTitle}</h3>
              <p className="app-copy mt-2">{t.importDesc}</p>
            </div>
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
              <div className="space-y-4">
                <label className="app-field">
                  <span className="app-field-label">{t.file}</span>
                  <input type="file" accept=".txt,.md,.csv,text/plain,text/markdown,text/csv" className="app-input" onChange={(event) => void handleImportFile(event)} />
                  <p className="mt-2 text-sm text-slate-500">{selectedFileName ? `${t.fileLoaded}: ${selectedFileName}` : t.fileHint}</p>
                </label>
                <TextField label={t.raw} value={rawImportText} onChange={(value) => { setRawImportText(value); setPreview(null); }} multiline />
                <label className="app-toggle">
                  <input type="checkbox" checked={useLlmFallback} disabled={!providerReady} onChange={(event) => setUseLlmFallback(event.target.checked)} />
                  {t.fallback}
                </label>
                {!providerReady ? <p className="text-sm text-slate-500">{t.providerHint}</p> : null}
                <button type="button" onClick={() => void previewImport()} disabled={previewing} className="app-button-primary disabled:cursor-not-allowed disabled:bg-slate-400">
                  {previewing ? dictionary.loading : t.preview}
                </button>
              </div>
              <div className="app-subcard p-5">
                <div className="border-b border-slate-200/70 pb-3">
                  <div className="text-sm font-semibold text-slate-900">{t.formats}</div>
                </div>
                <div className="mt-4 space-y-4">
                  <FormatExample title={t.formatOneTitle} example={examples.titleUrl} />
                  <FormatExample title={t.formatTwoTitle} example={examples.markdown} />
                  <FormatExample title={t.formatThreeTitle} example={examples.urlOnly} />
                  <FormatExample title={t.formatFourTitle} example={examples.csv} hint={t.csvHint} />
                </div>
              </div>
            </div>
          </div>

          {preview ? (
            <div className="app-panel p-6 sm:p-7">
              <div className="app-section-head">
                <p className="app-kicker">Preview</p>
                <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{t.previewTitle}</h3>
                <p className="app-copy mt-2">{preview.used_llm_fallback ? t.usedLlm : t.bindingHint}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label={t.parsed} value={String(preview.importable_count)} />
                <Metric label={t.dup} value={String(preview.duplicate_count)} />
                <Metric label={t.invalid} value={String(preview.invalid_count)} />
              </div>
              <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
                <div className="space-y-4">
                  <PreviewPanel title={t.parsed} subtitle={t.previewCount(preview.parsed_items.length)} empty={t.previewFirst} items={preview.parsed_items.map((item) => ({ title: item.title, meta: item.url }))} />
                  <PreviewPanel title={t.dup} subtitle={t.previewCount(preview.duplicate_items.length)} empty={t.previewFirst} items={preview.duplicate_items.map((item) => ({ title: item.title, meta: item.url }))} />
                  <PreviewPanel title={t.invalid} subtitle={t.previewCount(preview.invalid_items.length)} empty={t.previewFirst} items={preview.invalid_items.map((item) => ({ title: item.reason, meta: item.raw }))} />
                </div>
                <div className="app-subcard p-5">
                  <div className="border-b border-slate-200/70 pb-3">
                    <div className="text-sm font-semibold text-slate-900">{t.binding}</div>
                  </div>
                  <div className="mt-4 space-y-3">
                    <label className="app-toggle"><input type="radio" checked={bindingMode === "none"} onChange={() => setBindingMode("none")} />{t.noBinding}</label>
                    <label className="app-toggle"><input type="radio" checked={bindingMode === "existing"} onChange={() => setBindingMode("existing")} />{t.existing}</label>
                    {bindingMode === "existing" ? (
                      <label className="app-field">
                        <span className="app-field-label">{dictionary.articleSource}</span>
                        <select className="app-select" value={selectedSourceId} onChange={(event) => setSelectedSourceId(event.target.value)}>
                          <option value="">{dictionary.sourceUnknown}</option>
                          {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
                        </select>
                      </label>
                    ) : null}
                    <label className="app-toggle"><input type="radio" checked={bindingMode === "new"} onChange={() => setBindingMode("new")} />{t.manual}</label>
                    {bindingMode === "new" ? (
                      <div className="space-y-4 rounded-[24px] border border-slate-200/70 bg-white/75 p-4">
                        <TextField label={dictionary.formName} value={manualSourceDraft.name} onChange={(value) => setManualSourceDraft((current) => ({ ...current, name: value }))} />
                        <TextField label={dictionary.formHomepage} value={manualSourceDraft.homepage_url ?? ""} onChange={(value) => setManualSourceDraft((current) => ({ ...current, homepage_url: value || null }))} />
                        <div className="grid gap-4 sm:grid-cols-2">
                          <TextField label={dictionary.formLanguage} value={manualSourceDraft.language} onChange={(value) => setManualSourceDraft((current) => ({ ...current, language: value }))} />
                          <label className="app-field">
                            <span className="app-field-label">{dictionary.formPriority}</span>
                            <input type="number" className="app-input" value={manualSourceDraft.priority} onChange={(event) => setManualSourceDraft((current) => ({ ...current, priority: Number(event.target.value) }))} />
                          </label>
                        </div>
                        <label className="app-toggle"><input type="checkbox" checked={manualSourceDraft.is_active} onChange={(event) => setManualSourceDraft((current) => ({ ...current, is_active: event.target.checked }))} />{dictionary.formActive}</label>
                        <p className="text-sm text-slate-500">{t.createHint}</p>
                      </div>
                    ) : null}
                    <label className="app-toggle mt-2"><input type="checkbox" checked={analyzeAfterImport} disabled={!providerReady} onChange={(event) => setAnalyzeAfterImport(event.target.checked)} />{t.analyze}</label>
                    <button type="button" onClick={() => void importPreview()} disabled={importing || preview.parsed_items.length === 0} className="app-button-primary mt-2 w-full disabled:cursor-not-allowed disabled:bg-slate-400">
                      {importing ? dictionary.loading : t.importNow}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          <div className="app-panel p-5">
            <div className="grid gap-3 md:grid-cols-3">
              <FilterSelect label={dictionary.filterBySource} value={filters.source_id} onChange={(value) => setFilters((current) => ({ ...current, source_id: value }))} options={[{ value: "", label: dictionary.all }, ...sources.map((source) => ({ value: String(source.id), label: source.name }))]} />
              <FilterSelect label={dictionary.filterByStatus} value={filters.status} onChange={(value) => setFilters((current) => ({ ...current, status: value }))} options={[{ value: "", label: dictionary.all }, { value: "planned", label: labelForStatus(language, "planned") }, { value: "skimmed", label: labelForStatus(language, "skimmed") }, { value: "deep_read", label: labelForStatus(language, "deep_read") }]} />
              <FilterSelect label={dictionary.filterByDifficulty} value={filters.difficulty} onChange={(value) => setFilters((current) => ({ ...current, difficulty: value }))} options={[{ value: "", label: dictionary.all }, { value: "beginner", label: labelForDifficulty(language, "beginner") }, { value: "intermediate", label: labelForDifficulty(language, "intermediate") }, { value: "advanced", label: labelForDifficulty(language, "advanced") }]} />
            </div>
          </div>

          {articles.length === 0 ? <EmptyState title={dictionary.empty} description={dictionary.inboxDescription} /> : articles.map((article) => (
            <article key={article.id} className="app-panel p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <ArticleTitleLink title={article.title} url={article.url} className="text-xl font-semibold text-slate-950" />
                    <StatusBadge label={labelForStatus(language, article.status)} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{sourceLookup.get(article.source_id ?? -1) || article.source_name_snapshot || dictionary.sourceUnknown}</p>
                  <a className="mt-2 inline-flex text-sm font-medium text-sky-700 hover:text-sky-900" href={article.url} target="_blank" rel="noreferrer">{article.url}</a>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge label={labelForDifficulty(language, article.difficulty)} tone="warning" />
                  <StatusBadge label={article.stage ? labelForStage(language, article.stage) : "Inbox"} tone={article.stage ? "success" : "neutral"} />
                </div>
              </div>
              {article.raw_summary ? <p className="mt-4 text-sm leading-7 text-slate-600">{article.raw_summary}</p> : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="app-subcard px-4 py-3"><div className="app-stat-label">{label}</div><div className="mt-2 text-lg font-semibold text-slate-900">{value}</div></div>;
}

function FormatExample({ title, example, hint }: { title: string; example: string; hint?: string }) {
  return (
    <div>
      <div className="font-medium text-slate-900">{title}</div>
      <pre className="mt-2 whitespace-pre-wrap break-words rounded-2xl border border-slate-200/70 bg-slate-950 px-4 py-3 text-xs leading-6 text-slate-100">{example}</pre>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

function PreviewPanel({ title, subtitle, empty, items }: { title: string; subtitle: string; empty: string; items: { title: string; meta: string }[] }) {
  return (
    <div className="app-subcard p-4">
      <div className="border-b border-slate-200/70 pb-3">
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{subtitle}</div>
      </div>
      <div className="mt-3 space-y-3">
        {items.length === 0 ? <p className="text-sm text-slate-500">{empty}</p> : items.slice(0, 8).map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-2xl border border-slate-200/70 bg-white/80 p-3">
            <div className="text-sm font-medium text-slate-900">{item.title}</div>
            <div className="mt-1 break-all text-xs text-slate-500">{item.meta}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TextField({ label, value, onChange, required = false, multiline = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; multiline?: boolean }) {
  return (
    <label className="app-field">
      <span className="app-field-label">{label}</span>
      {multiline ? <textarea className="app-textarea" value={value} required={required} onChange={(event) => onChange(event.target.value)} /> : <input className="app-input" value={value} required={required} onChange={(event) => onChange(event.target.value)} />}
    </label>
  );
}

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) {
  return (
    <label className="app-field">
      <span className="app-field-label">{label}</span>
      <select className="app-select" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={`${label}-${option.value}`} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}
