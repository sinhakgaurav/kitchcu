import { useEffect, useState } from "react";
import { LiveCapturePhotoField } from "../../components/LiveCapturePhotoField";
import { RichTextEditor } from "../../components/RichTextEditor";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  computeChefRankings,
  fetchChefRankings,
  fetchRewardBalance,
  fetchSharedRecipes,
  redeemRewardPoints,
  shareCommunityRecipe,
  type ChefRankingEntry,
  type RewardBalance,
  type SharedRecipe,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function CommunityPage() {
  const { kitchen } = useKitchen();
  const [recipes, setRecipes] = useState<SharedRecipe[]>([]);
  const [rewards, setRewards] = useState<RewardBalance | null>(null);
  const [rankings, setRankings] = useState<ChefRankingEntry[]>([]);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    if (!kitchen) return;
    try {
      const [recipeRes, rewardRes, rankRes] = await Promise.all([
        fetchSharedRecipes(kitchen.id),
        fetchRewardBalance(kitchen.id),
        fetchChefRankings("city", kitchen.city ?? undefined),
      ]);
      setRecipes(recipeRes.recipes);
      setRewards(rewardRes);
      setRankings(rankRes.rankings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load community data");
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const onShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen || !title.trim()) return;
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await shareCommunityRecipe(kitchen.id, {
        title: title.trim(),
        summary: summary.trim() || undefined,
        recipe_html: bodyHtml || "<p>Shared recipe</p>",
        cover_url: coverUrl.trim() || undefined,
      });
      setTitle("");
      setSummary("");
      setBodyHtml("");
      setCoverUrl("");
      setMsg("Recipe shared with the community.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Share failed");
    } finally {
      setBusy(false);
    }
  };

  const onRedeem = async (type: "subscription_discount" | "featured_listing") => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const res = await redeemRewardPoints(kitchen.id, type);
      setMsg(`Redeemed ${res.points_spent} points — balance ${res.points_balance}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Redeem failed");
    } finally {
      setBusy(false);
    }
  };

  const onComputeRankings = async () => {
    if (!kitchen) return;
    setBusy(true);
    try {
      const res = await computeChefRankings(kitchen.id, "city", kitchen.city ?? "Pune");
      setRankings(res.rankings);
      setMsg(`Rankings updated for ${res.period}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ranking compute failed");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Community"
      title="Community"
      description="Share recipes, earn reward points, climb chef rankings (F23–F24)"
    >
      {error && <p className="form-error">{error}</p>}
      {msg && <div className="auth-card__success">{msg}</div>}

      <OwnerPanel
        title="Reward points"
        description="10 pts per appreciation · 100 = subscription discount · 500 = featured listing"
        action={
          <strong style={{ fontSize: "1.25rem" }}>{rewards?.points_balance ?? 0} pts</strong>
        }
      >
        <div className="owner-actions">
          <button
            type="button"
            className="btn btn--ghost"
            disabled={busy}
            onClick={() => onRedeem("subscription_discount")}
          >
            Redeem subscription discount (100)
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={busy}
            onClick={() => onRedeem("featured_listing")}
          >
            Redeem featured listing (500)
          </button>
        </div>
      </OwnerPanel>

      <OwnerPanel title="Share an original recipe">
        <form className="owner-form" onSubmit={onShare}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Grandma's dal tadka" />
          </label>
          <label>
            Summary
            <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Short pitch for the community" />
          </label>
          <div className="kc-field">
            <span className="kc-field__label">Cover photo</span>
            <LiveCapturePhotoField
              kitchenId={kitchen.id}
              context="general"
              value={coverUrl}
              onChange={setCoverUrl}
              label="Recipe cover"
            />
          </div>
          <div className="kc-field">
            <span className="kc-field__label">Recipe (rich text — inline images supported)</span>
            <RichTextEditor
              value={bodyHtml}
              onChange={setBodyHtml}
              kitchenId={kitchen.id}
              uploadContext="general"
              placeholder="Steps, quality notes, tips…"
              minHeight={140}
            />
          </div>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            Share to community
          </button>
        </form>
      </OwnerPanel>

      <OwnerPanel title="Your shared recipes">
        {recipes.length === 0 ? (
          <OwnerEmpty message="No shared recipes yet — share your first original recipe above." />
        ) : (
          <ul className="owner-detail-items">
            {recipes.map((r) => (
              <li key={r.id}>
                {r.cover_url ? (
                  <img src={r.cover_url} alt="" className="owner-thumb" style={{ marginRight: "0.5rem" }} />
                ) : null}
                <strong>{r.title}</strong> — {r.appreciation_count} appreciations · {r.points_earned} pts earned
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>

      <OwnerPanel
        title="City chef rankings"
        description={`Top kitchens in ${kitchen.city ?? "your city"}`}
        action={
          <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={onComputeRankings}>
            Refresh rankings
          </button>
        }
      >
        {rankings.length === 0 ? (
          <OwnerEmpty message="No rankings yet — tap refresh after you have delivered orders this month." />
        ) : (
          <ol className="owner-rankings">
            {rankings.map((r) => (
              <li key={r.kitchen_id} className={r.kitchen_id === kitchen.id ? "owner-rankings__you" : undefined}>
                <span>#{r.rank}</span>
                <span>{r.kitchen_name} ({r.kitchen_code})</span>
                <strong>{r.score.toFixed(1)}</strong>
              </li>
            ))}
          </ol>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
