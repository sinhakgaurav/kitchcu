import { useTranslation } from "react-i18next";

import { changeAppLocale } from "./index";
import { LANGUAGES, type LocaleCode } from "./languages";
import { persistLocaleChoice } from "./storage";

const OPTIONS = Object.values(LANGUAGES);

/** Compact language control for nav / settings after first choice. */
export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { i18n, t } = useTranslation();
  const current = (i18n.language?.split("-")[0] || "en") as LocaleCode;

  return (
    <label className={`lang-switcher ${className}`.trim()}>
      <span className="lang-switcher__label">{t("lang.change")}</span>
      <select
        value={LANGUAGES[current] ? current : "en"}
        onChange={async (e) => {
          const code = e.target.value as LocaleCode;
          persistLocaleChoice(code);
          await changeAppLocale(code);
        }}
      >
        {OPTIONS.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nameEn}
            {lang.code !== "en" ? ` · ${lang.name}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
