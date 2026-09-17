import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useReportFoodFilter, type ReportFoodDiet } from "../hooks/useReportFoodFilter";

const VARIETY_OPTIONS = ["veg", "vegan"] as const;

type Props = {
  variant?: "nearby" | "hero" | "menu";
  diet?: string;
  onDietChange?: (diet: ReportFoodDiet) => void;
};

export function ReportFoodFilter({ variant = "nearby", diet = "", onDietChange }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { signedIn, hasReport, enabled, preferCategories, busy, error, setEnabled, announceDiet } =
    useReportFoodFilter();

  const preferSet = new Set(preferCategories.map((c) => c.toLowerCase()));
  const varieties = VARIETY_OPTIONS.filter((slug) => preferSet.has(slug));

  const value = !signedIn || !hasReport || !enabled
    ? "off"
    : diet && varieties.includes(diet as (typeof VARIETY_OPTIONS)[number])
      ? diet
      : "match";

  const onChange = async (raw: string) => {
    try {
      if (raw === "need-signin") {
        navigate("/login?next=/");
        return;
      }
      if (raw === "need-upload") {
        navigate("/dashboard?tab=health");
        return;
      }
      if (raw === "off") {
        if (enabled) await setEnabled(false);
        return;
      }
      if (raw === "match") {
        onDietChange?.("");
        if (enabled) announceDiet("");
        else await setEnabled(true, "");
        return;
      }
      if (raw === "veg" || raw === "vegan") {
        onDietChange?.(raw);
        if (enabled) announceDiet(raw);
        else await setEnabled(true, raw);
      }
    } catch {
      /* Error copy is stored on the hook */
    }
  };

  return (
    <label className={`report-food-filter report-food-filter--${variant}`}>
      <span className={variant === "hero" ? "visually-hidden" : undefined}>
        {t("customer.discovery.reportFood")}
      </span>
      <select
        value={value}
        disabled={busy}
        aria-label={t("customer.discovery.reportFood")}
        onChange={(e) => {
          void onChange(e.target.value);
        }}
      >
        <option value="off">{t("customer.discovery.reportFoodAll")}</option>
        {!signedIn ? (
          <option value="need-signin">{t("customer.discovery.reportFoodSignIn")}</option>
        ) : !hasReport ? (
          <option value="need-upload">{t("customer.discovery.reportFoodNeedUpload")}</option>
        ) : (
          <>
            <option value="match">{t("customer.discovery.reportFoodMatch")}</option>
            {varieties.map((slug) => (
              <option key={slug} value={slug}>
                {t("customer.discovery.reportFoodVariety", {
                  variety: t(`customer.discovery.reportFood_${slug}`),
                })}
              </option>
            ))}
          </>
        )}
      </select>
      {error ? <span className="report-food-filter__error">{error}</span> : null}
    </label>
  );
}
