import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { DEFAULT_LOCALE, type LocaleCode } from "./languages";
import { initialLocale } from "./storage";

import en from "./locales/en.json";
import hi from "./locales/hi.json";
import mr from "./locales/mr.json";
import ta from "./locales/ta.json";
import te from "./locales/te.json";
import kn from "./locales/kn.json";
import ml from "./locales/ml.json";
import bn from "./locales/bn.json";
import gu from "./locales/gu.json";
import pa from "./locales/pa.json";
import bho from "./locales/bho.json";
import mai from "./locales/mai.json";

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  mr: { translation: mr },
  ta: { translation: ta },
  te: { translation: te },
  kn: { translation: kn },
  ml: { translation: ml },
  bn: { translation: bn },
  gu: { translation: gu },
  pa: { translation: pa },
  bho: { translation: bho },
  mai: { translation: mai },
} as const;

let ready: Promise<typeof i18n> | null = null;

export function initI18n(locale?: LocaleCode): Promise<typeof i18n> {
  if (ready) return ready;
  const lng = locale ?? initialLocale();
  ready = i18n.use(initReactI18next).init({
    resources,
    lng,
    fallbackLng: DEFAULT_LOCALE,
    interpolation: { escapeValue: false },
    returnNull: false,
  }).then(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = lng;
    }
    return i18n;
  });
  return ready;
}

export async function changeAppLocale(code: LocaleCode): Promise<void> {
  await initI18n();
  await i18n.changeLanguage(code);
  if (typeof document !== "undefined") {
    document.documentElement.lang = code;
  }
}

export { i18n };
export default i18n;
