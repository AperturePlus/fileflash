import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import type { AppLanguage } from '../types/user';
import { DEFAULT_LANGUAGE, LOCALE_MESSAGES, type LocaleKey } from '../i18n/messages';

const LANGUAGE_STORAGE_KEY = 'fileflash-locale';
const SUPPORTED_LANGUAGES: AppLanguage[] = ['zh-CN', 'en-US'];

function isSupportedLanguage(value: string | null | undefined): value is AppLanguage {
  if (!value) {
    return false;
  }
  return SUPPORTED_LANGUAGES.includes(value as AppLanguage);
}

function normalizeLanguage(value: string | null | undefined): AppLanguage {
  return isSupportedLanguage(value) ? value : DEFAULT_LANGUAGE;
}

function applyDocumentLanguage(language: AppLanguage) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', language);
  }
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<AppLanguage>(normalizeLanguage(localStorage.getItem(LANGUAGE_STORAGE_KEY)));

  function setLocale(nextLanguage: AppLanguage) {
    locale.value = normalizeLanguage(nextLanguage);
  }

  function t(key: LocaleKey): string {
    return LOCALE_MESSAGES[locale.value][key] || LOCALE_MESSAGES[DEFAULT_LANGUAGE][key] || key;
  }

  watch(
    locale,
    (nextLanguage) => {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
      applyDocumentLanguage(nextLanguage);
    },
    { immediate: true },
  );

  return {
    locale,
    supportedLanguages: SUPPORTED_LANGUAGES,
    setLocale,
    t,
  };
});
