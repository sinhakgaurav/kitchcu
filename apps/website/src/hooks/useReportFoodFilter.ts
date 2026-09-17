import { useCallback, useEffect, useState } from "react";
import {
  fetchCustomerDietProfile,
  updateCustomerDietFilter,
  type CustomerDietProfile,
} from "../shared/customerApi";
import { isCustomerSignedIn, useCustomerAuth } from "../shared/customerAuth";

export const DIET_FILTER_CHANGED = "ckac:diet-filter-changed";

export type ReportFoodDiet = "" | "veg" | "non_veg" | "vegan";

export type ReportFoodChangeDetail = {
  enabled: boolean;
  diet?: ReportFoodDiet;
};

export function useReportFoodFilter() {
  const { session } = useCustomerAuth();
  const signedIn = isCustomerSignedIn(session);
  const [profile, setProfile] = useState<CustomerDietProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!signedIn) {
      setProfile(null);
      return;
    }
    try {
      setProfile(await fetchCustomerDietProfile());
    } catch {
      setProfile(null);
    }
  }, [signedIn]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    const onChange = () => {
      void reload();
    };
    window.addEventListener(DIET_FILTER_CHANGED, onChange);
    return () => window.removeEventListener(DIET_FILTER_CHANGED, onChange);
  }, [reload]);

  const setEnabled = useCallback(
    async (enabled: boolean, diet?: ReportFoodDiet) => {
      setBusy(true);
      setError("");
      try {
        const next = await updateCustomerDietFilter(enabled);
        setProfile(next);
        window.dispatchEvent(
          new CustomEvent<ReportFoodChangeDetail>(DIET_FILTER_CHANGED, {
            detail: { enabled: next.diet_filter_enabled, diet },
          }),
        );
        return next;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not update the report filter");
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const announceDiet = useCallback((diet: ReportFoodDiet) => {
    window.dispatchEvent(
      new CustomEvent<ReportFoodChangeDetail>(DIET_FILTER_CHANGED, {
        detail: { enabled: Boolean(profile?.diet_filter_enabled), diet },
      }),
    );
  }, [profile?.diet_filter_enabled]);

  return {
    signedIn,
    profile,
    hasReport: Boolean(profile?.has_checkup_report),
    enabled: Boolean(profile?.diet_filter_enabled),
    preferCategories: profile?.prefer_categories ?? [],
    busy,
    error,
    setEnabled,
    announceDiet,
    reload,
  };
}
