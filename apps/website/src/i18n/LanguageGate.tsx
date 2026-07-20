import { useEffect, useState, type ReactNode } from "react";
import { I18nextProvider, useTranslation } from "react-i18next";

import { changeAppLocale, i18n, initI18n } from "./index";
import { detectSuggestedLocale, type DetectedLocale } from "./detectLocale";
import { LANGUAGES, LOCALE_PICKER_ORDER, type LocaleCode } from "./languages";
import { hasChosenLocale, persistLocaleChoice, readStoredLocale } from "./storage";

type GateState =
  | { phase: "boot" }
  | { phase: "ready"; skipPrompt: true }
  | { phase: "prompt"; detected: DetectedLocale };

function LanguageChooser({
  detected,
  onChoose,
}: {
  detected: DetectedLocale;
  onChoose: (code: LocaleCode) => void;
}) {
  const { t } = useTranslation();
  const suggested = detected.suggested;
  const local = LANGUAGES[suggested];
  const strongGeo = detected.source === "geo" && detected.confidence === "high";

  if (strongGeo && suggested !== "en") {
    const localLabel = local.nameEn;
    const localNative = local.name;
    return (
      <div className="lang-gate" role="dialog" aria-modal="true" aria-labelledby="lang-gate-title">
        <div className="lang-gate__card">
          <p className="lang-gate__eyebrow">kitchCU</p>
          <h1 id="lang-gate-title">{t("lang.title")}</h1>
          <p>
            {t("lang.detectedLocation", { language: localLabel })}{" "}
            {t("lang.ask", { language: localLabel })}
          </p>
          <div className="lang-gate__actions">
            <button type="button" className="btn btn--ghost btn--lg" onClick={() => onChoose("en")}>
              {t("lang.continueEn")}
            </button>
            <button
              type="button"
              className="btn btn--primary btn--lg"
              onClick={() => onChoose(suggested)}
            >
              {t("lang.continueLocal", {
                language:
                  localNative !== localLabel ? `${localLabel} (${localNative})` : localLabel,
              })}
            </button>
          </div>
          <p className="lang-gate__more-hint">{t("lang.orPickBelow")}</p>
          <div className="lang-gate__grid" role="list">
            {LOCALE_PICKER_ORDER.filter((c) => c !== "en" && c !== suggested).map((code) => (
              <button
                key={code}
                type="button"
                className="lang-gate__lang"
                role="listitem"
                onClick={() => onChoose(code)}
              >
                <strong>{LANGUAGES[code].nameEn}</strong>
                <span>{LANGUAGES[code].name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Browser / default — do not claim "location detected Hindi" for MH users on hi-IN devices
  return (
    <div className="lang-gate" role="dialog" aria-modal="true" aria-labelledby="lang-gate-title">
      <div className="lang-gate__card lang-gate__card--wide">
        <p className="lang-gate__eyebrow">kitchCU</p>
        <h1 id="lang-gate-title">{t("lang.title")}</h1>
        <p>{t("lang.pickHint")}</p>
        {detected.source === "browser" && suggested !== "en" && (
          <p className="lang-gate__soft">
            {t("lang.browserHint", { language: LANGUAGES[suggested].nameEn })}
          </p>
        )}
        <div className="lang-gate__grid" role="list">
          {LOCALE_PICKER_ORDER.map((code) => (
            <button
              key={code}
              type="button"
              className={`lang-gate__lang${code === suggested ? " lang-gate__lang--suggested" : ""}`}
              role="listitem"
              onClick={() => onChoose(code)}
            >
              <strong>{LANGUAGES[code].nameEn}</strong>
              <span>{LANGUAGES[code].name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function LanguageGateInner({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [state, setState] = useState<GateState>({ phase: "boot" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await initI18n(readStoredLocale() ?? undefined);
      if (cancelled) return;

      if (hasChosenLocale()) {
        setState({ phase: "ready", skipPrompt: true });
        return;
      }

      const detected = await detectSuggestedLocale();
      if (cancelled) return;

      // Only auto-skip when we are sure English is appropriate (outside India / default)
      if (detected.suggested === "en" && detected.source === "default") {
        persistLocaleChoice("en");
        await changeAppLocale("en");
        setState({ phase: "ready", skipPrompt: true });
        return;
      }

      setState({ phase: "prompt", detected });
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const choose = async (code: LocaleCode) => {
    persistLocaleChoice(code);
    await changeAppLocale(code);
    setState({ phase: "ready", skipPrompt: true });
  };

  if (state.phase === "boot") {
    return (
      <div className="lang-gate lang-gate--boot" aria-busy="true">
        <p className="lang-gate__boot">{t("lang.detecting")}</p>
      </div>
    );
  }

  if (state.phase === "prompt") {
    return <LanguageChooser detected={state.detected} onChoose={choose} />;
  }

  return <>{children}</>;
}

/** Wraps portal / customer / kitchen apps: detect locale, ask EN vs local once. */
export function LanguageGate({ children }: { children: ReactNode }) {
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    initI18n().finally(() => setBooted(true));
  }, []);

  if (!booted) {
    return (
      <div className="lang-gate lang-gate--boot" aria-busy="true">
        <p className="lang-gate__boot">Loading…</p>
      </div>
    );
  }

  return (
    <I18nextProvider i18n={i18n}>
      <LanguageGateInner>{children}</LanguageGateInner>
    </I18nextProvider>
  );
}
