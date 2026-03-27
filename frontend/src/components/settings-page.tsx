"use client";

import { useEffect, useState } from "react";

import { useI18n } from "@/components/language-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import type { SettingsPayload } from "@/lib/types";

const emptySettings: SettingsPayload = {
  llm_provider_name: "",
  llm_base_url: "",
  llm_api_key: "",
  llm_model: "",
  llm_enabled: false,
  ui_language: "zh-CN",
};

export function SettingsPage() {
  const { dictionary, settings, reloadSettings, setLanguageOptimistic } = useI18n();
  const [form, setForm] = useState<SettingsPayload>(emptySettings);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const providerReady =
    !!form.llm_enabled && !!form.llm_api_key.trim() && !!form.llm_model.trim();
  const testConnectionLabel = form.ui_language === "zh-CN" ? "测试连接" : "Test connection";
  const testingLabel = form.ui_language === "zh-CN" ? "测试中..." : "Testing...";
  const missingConnectionFieldsLabel =
    form.ui_language === "zh-CN"
      ? "填写 API Key 和模型后即可测试。"
      : "Add an API key and model to test the connection.";

  const submit = async () => {
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

  const testConnection = async () => {
    if (!form.llm_api_key.trim() || !form.llm_model.trim()) {
      setError(
        form.ui_language === "zh-CN"
          ? "请先填写 API Key 和模型。"
          : "Please add both an API key and model before testing.",
      );
      setMessage(null);
      return;
    }

    setTesting(true);
    setError(null);
    setMessage(null);

    try {
      const result = await api.testSettingsConnection(form);
      setMessage(result.message);
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Connection test failed.");
    } finally {
      setTesting(false);
    }
  };

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Provider"
        title={dictionary.settingsTitle}
        description={dictionary.settingsDescription}
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <StatusBadge
          label={providerReady ? dictionary.providerConfigured : dictionary.providerMissing}
          tone={providerReady ? "success" : "warning"}
        />
        {!providerReady ? (
          <span className="text-sm text-slate-600">{dictionary.llmNotConfigured}</span>
        ) : null}
      </div>

      <div className="app-panel max-w-4xl p-6 sm:p-7">
        <div className="app-section-head">
          <p className="app-kicker">Provider</p>
          <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-slate-950">Configuration</h3>
          <p className="app-copy mt-2">
            Use any OpenAI-compatible endpoint and keep language settings alongside it.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label={dictionary.formProviderName}
            value={form.llm_provider_name}
            onChange={(value) =>
              setForm((current) => ({ ...current, llm_provider_name: value }))
            }
            placeholder="OpenAI compatible"
          />
          <TextField
            label={dictionary.formProviderModel}
            value={form.llm_model}
            onChange={(value) =>
              setForm((current) => ({ ...current, llm_model: value }))
            }
            placeholder="gpt-4.1-mini"
          />
        </div>

        <div className="mt-4 grid gap-4">
          <TextField
            label={dictionary.formProviderBaseUrl}
            value={form.llm_base_url}
            onChange={(value) =>
              setForm((current) => ({ ...current, llm_base_url: value }))
            }
            placeholder="https://api.openai.com/v1"
          />
          <TextField
            label={dictionary.formProviderApiKey}
            value={form.llm_api_key}
            onChange={(value) =>
              setForm((current) => ({ ...current, llm_api_key: value }))
            }
            placeholder="sk-..."
          />
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="app-field">
            <span className="app-field-label">
              {dictionary.formUiLanguage}
            </span>
            <select
              className="app-select"
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

          <label className="app-toggle">
            <input
              type="checkbox"
              checked={form.llm_enabled}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  llm_enabled: event.target.checked,
                }))
              }
            />
            {dictionary.formProviderEnabled}
          </label>
        </div>

        {message ? (
          <div className="app-alert app-alert-success mt-5">
            {message}
          </div>
        ) : null}
        {error ? (
          <div className="app-alert app-alert-error mt-5">
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={testing || saving}
            onClick={testConnection}
            className="app-button-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {testing ? testingLabel : testConnectionLabel}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={submit}
            className="app-button-primary disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {saving ? dictionary.loading : dictionary.save}
          </button>
        </div>
        {!form.llm_api_key.trim() || !form.llm_model.trim() ? (
          <p className="mt-3 text-sm text-slate-500">{missingConnectionFieldsLabel}</p>
        ) : null}
      </div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder = "",
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
