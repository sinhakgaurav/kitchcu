import { useEffect, useState, type ReactNode } from "react";
import { I18nextProvider, useTranslation } from "react-i18next";

import { changeAppLocale, i18n, initI18n } from "./index";
import { detectSuggestedLocale } from "./detectLocale";
import { LANGUAGES, type LocaleCode } from "./languages";
import { hasChosenLocale, persistLocaleChoice, readStoredLocale } from "./storage";

type GateState =
  | { phase: "boot" }
  | { phase: "ready"; skipPrompt: true }
  | { phase: "prompt"; suggested: LocaleCode };

function LanguageChooser({
  suggested,
  onChoose,
}: {
  suggested: LocaleCode;
  onChoose: (code: LocaleCode) => void;
}) {
  const { t } = useTranslation();
  const local = LANGUAGES[suggested];
  const localLabel = local.nameEn;
  const localNative = local.name;

  return (
    <div className="lang-gate" role="dialog" aria-modal="true" aria-labelledby="lang-gate-title">
      <div className="lang-gate__card">
        <p className="lang-gate__eyebrow">kitchCU</p>
        <h1 id="lang-gate-title">{t("lang.title")}</h1>
        <p>
          {t("lang.detected", { language: localLabel })}{" "}
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
            {t("lang.continueLocal", { language: localNative !== localLabel ? `${localLabel} (${localNative})` : localLabel })}
          </button>
        </div>
      </div>
    </div>
  );
}

function LanguageGateInner({ children }: { children: ReactNode }) {
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

      // English suggestion → no chooser; persist and continue
      if (detected.suggested === "en") {
        persistLocaleChoice("en");
        await changeAppLocale("en");
        setState({ phase: "ready", skipPrompt: true });
        return;
      }

      setState({ phase: "prompt", suggested: detected.suggested });
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
        <p className="lang-gate__boot">Detecting your location…</p>
      </div>
    );
  }

  if (state.phase === "prompt") {
    return <LanguageChooser suggested={state.suggested} onChoose={choose} />;
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
