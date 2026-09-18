import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { OrderItem } from "../shared/api";
import { submitOrderRatings, type HealthNudge } from "../shared/customerRatingsApi";

type Props = {
  orderId: string;
  item: OrderItem;
  canRate: boolean;
  onRated: (result: {
    dishId: string;
    home_taste: number;
    quality: number;
    health_nudge: HealthNudge;
  }) => void;
  onError: (message: string) => void;
};

function StarRow({
  label,
  value,
  disabled,
  name,
  onPick,
}: {
  label: string;
  value: number;
  disabled: boolean;
  name: string;
  onPick?: (score: number) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="customer-stars-row">
      <span className="customer-stars-row__label">{label}</span>
      <div className="customer-stars" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((score) => {
          const on = score <= value;
          return (
            <button
              key={score}
              type="button"
              role="radio"
              aria-checked={score === value}
              aria-label={t("customer.orders.rateStars", { name: `${name} ${label}`, score })}
              className={`customer-stars__star${on ? " customer-stars__star--on" : ""}`}
              disabled={disabled}
              onClick={() => onPick?.(score)}
            >
              ★
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function OrderDishRatings({ orderId, item, canRate, onRated, onError }: Props) {
  const { t } = useTranslation();
  const givenTaste = item.rating_home_taste ?? null;
  const givenQuality = item.rating_quality ?? null;
  const alreadyRated = givenTaste != null && givenQuality != null;
  const [taste, setTaste] = useState<number>(givenTaste ?? 0);
  const [quality, setQuality] = useState<number>(givenQuality ?? 0);
  const [showQuality, setShowQuality] = useState(alreadyRated);
  const [busy, setBusy] = useState(false);

  const save = async (homeTaste: number, qualityScore: number) => {
    if (busy || alreadyRated || !canRate) return;
    setBusy(true);
    try {
      const result = await submitOrderRatings(orderId, [
        {
          dish_id: item.dish_id,
          home_taste_score: homeTaste,
          quality_score: qualityScore,
        },
      ]);
      onRated({
        dishId: item.dish_id,
        home_taste: homeTaste,
        quality: qualityScore,
        health_nudge: result.health_nudge,
      });
    } catch (err) {
      onError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  if (alreadyRated) {
    return (
      <div className="customer-dish-rate customer-dish-rate--done">
        <StarRow label={t("customer.orders.homeTaste")} value={givenTaste} disabled name={item.dish_name} />
        <StarRow label={t("customer.orders.quality")} value={givenQuality} disabled name={item.dish_name} />
      </div>
    );
  }

  if (!canRate) return null;

  return (
    <div className="customer-dish-rate">
      <StarRow
        label={t("customer.orders.homeTaste")}
        value={taste}
        disabled={busy}
        name={item.dish_name}
        onPick={(score) => {
          setTaste(score);
          setQuality((prev) => (prev > 0 ? prev : score));
          setShowQuality(true);
        }}
      />
      {showQuality && (
        <StarRow
          label={t("customer.orders.quality")}
          value={quality}
          disabled={busy}
          name={item.dish_name}
          onPick={(score) => {
            setQuality(score);
            void save(taste || score, score);
          }}
        />
      )}
      {showQuality && taste > 0 && quality > 0 && (
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={busy}
          aria-busy={busy}
          onClick={() => void save(taste, quality)}
        >
          {busy ? t("customer.orders.savingRating") : t("customer.orders.saveRating")}
        </button>
      )}
    </div>
  );
}
