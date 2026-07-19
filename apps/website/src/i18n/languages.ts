/** Supported UI locales — English always available; others suggested by location. */

export type LocaleCode =
  | "en"
  | "hi"
  | "mr"
  | "ta"
  | "te"
  | "kn"
  | "ml"
  | "bn"
  | "gu"
  | "pa";

export type LanguageMeta = {
  code: LocaleCode;
  /** Endonym / display name shown in the chooser */
  name: string;
  /** English label for operators */
  nameEn: string;
};

export const LANGUAGES: Record<LocaleCode, LanguageMeta> = {
  en: { code: "en", name: "English", nameEn: "English" },
  hi: { code: "hi", name: "हिन्दी", nameEn: "Hindi" },
  mr: { code: "mr", name: "मराठी", nameEn: "Marathi" },
  ta: { code: "ta", name: "தமிழ்", nameEn: "Tamil" },
  te: { code: "te", name: "తెలుగు", nameEn: "Telugu" },
  kn: { code: "kn", name: "ಕನ್ನಡ", nameEn: "Kannada" },
  ml: { code: "ml", name: "മലയാളം", nameEn: "Malayalam" },
  bn: { code: "bn", name: "বাংলা", nameEn: "Bengali" },
  gu: { code: "gu", name: "ગુજરાતી", nameEn: "Gujarati" },
  pa: { code: "pa", name: "ਪੰਜਾਬੀ", nameEn: "Punjabi" },
};

export const DEFAULT_LOCALE: LocaleCode = "en";

export function isLocaleCode(value: string | null | undefined): value is LocaleCode {
  return !!value && value in LANGUAGES;
}

export function languageDisplayName(code: LocaleCode): string {
  return LANGUAGES[code].nameEn;
}
