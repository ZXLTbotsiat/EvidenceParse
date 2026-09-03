"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { Language, MessageKey, resolveLanguage, SUPPORTED_LANGUAGES, translate } from "./i18n-catalog";

const STORAGE_KEY = "evidence-parse-language";

type I18nValue = {
  language: Language;
  languages: typeof SUPPORTED_LANGUAGES;
  setLanguage: (language: Language) => void;
  t: (key: MessageKey, values?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("zh-CN");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setLanguage(resolveLanguage(window.localStorage.getItem(STORAGE_KEY) ?? window.navigator.language));
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    window.localStorage.setItem(STORAGE_KEY, language);
    document.documentElement.lang = language;
  }, [language, ready]);

  const value = useMemo<I18nValue>(() => ({
    language,
    languages: SUPPORTED_LANGUAGES,
    setLanguage,
    t: (key, values) => translate(language, key, values),
  }), [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}
