"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

import { api } from "@/lib/api";
import { getDictionary } from "@/lib/i18n";
import type { LanguageCode, SettingsPayload } from "@/lib/types";

type LanguageContextValue = {
  language: LanguageCode;
  dictionary: ReturnType<typeof getDictionary>;
  loading: boolean;
  settings: SettingsPayload | null;
  reloadSettings: () => Promise<void>;
  setLanguageOptimistic: (language: LanguageCode) => void;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<LanguageCode>("zh-CN");
  const [settings, setSettings] = useState<SettingsPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadSettings = async () => {
    try {
      const payload = await api.getSettings();
      setSettings(payload);
      setLanguage(payload.ui_language);
    } catch {
      setLanguage("zh-CN");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reloadSettings();
  }, []);

  const value = useMemo(
    () => ({
      language,
      dictionary: getDictionary(language),
      loading,
      settings,
      reloadSettings,
      setLanguageOptimistic: setLanguage,
    }),
    [language, loading, settings],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useI18n must be used within LanguageProvider.");
  }
  return context;
}
