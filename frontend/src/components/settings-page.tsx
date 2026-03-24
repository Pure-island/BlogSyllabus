"use client";

import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { api, ApiError } from "@/lib/api";
import type { SettingsPayload } from "@/lib/types";

export function SettingsPage() {
  const {
    dictionary,
    settings,
    reloadSettings,
    setLanguageOptimistic,
  } = useI18n();
  const [form, setForm] = useState<SettingsPayload>({
    openai_api_key: "",
    openai_model: "",
    ui_language: "zh-CN",
    openai_enabled: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      const saved = await api.updateSettings(form);
      setLanguageOptimistic(saved.ui_language);
      await reloadSettings();
      setMessage(dictionary.successSaved);
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Settings"
        title={dictionary.settingsTitle}
        description={dictionary.settingsDescription}
      />

      <form
        onSubmit={submit}
        className="max-w-3xl rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_45px_rgba(15,23,42,0.08)]"
      >
        <div className="grid gap-4">
          <TextField
            label={dictionary.formOpenAIKey}
            value={form.openai_api_key}
            onChange={(value) =>
              setForm((current) => ({ ...current, openai_api_key: value }))
            }
          />
          <TextField
            label={dictionary.formOpenAIModel}
            value={form.openai_model}
            onChange={(value) =>
              setForm((current) => ({ ...current, openai_model: value }))
            }
          />
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">{dictionary.formUiLanguage}</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
              value={form.ui_language}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  ui_language: event.target.value as SettingsPayload["ui_language"],
                }))
              }
            >
              <option value="zh-CN">{dictionary.languageChinese}</option>
              <option value="en">{dictionary.languageEnglish}</option>
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={form.openai_enabled}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  openai_enabled: event.target.checked,
                }))
              }
            />
            {dictionary.formOpenAIEnabled}
          </label>
        </div>

        {message ? (
          <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {message}
          </div>
        ) : null}
        {error ? (
          <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={saving}
          className="mt-6 rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {saving ? dictionary.loading : dictionary.save}
        </button>
      </form>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-slate-700">{label}</span>
      <input
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-sky-400 focus:bg-white"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
