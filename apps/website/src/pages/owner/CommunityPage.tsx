import { useEffect, useState } from "react";
import { RichTextEditor } from "../../components/RichTextEditor";
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
      });
      setTitle("");
      setSummary("");
      setBodyHtml("");
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
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Community</h1>
          <p className="owner-page__code">Share recipes, earn reward points, climb chef rankings (F23–F24)</p>
        </div>
      </header>

      {error && <p className="owner-error">{error}</p>}
      {msg && <p className="owner-success">{msg}</p>}

      <section className="glass owner-section">
        <h2>Reward points</h2>
        <p>
          Balance: <strong>{rewards?.points_balance ?? 0}</strong> pts
          <span className="owner-page__code"> · 10 pts per appreciation · 100 = subscription discount · 500 = featured listing</span>
        </p>
        <div className="owner-actions">
          <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => onRedeem("subscription_discount")}>
            Redeem subscription discount (100)
          </button>
          <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => onRedeem("featured_listing")}>
            Redeem featured listing (500)
          </button>
        </div>
      </section>

      <section className="glass owner-section">
        <h2>Share an original recipe</h2>
        <form className="owner-form" onSubmit={onShare}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Grandma's dal tadka" />
          </label>
          <label>
            Summary
            <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Short pitch for the community" />
          </label>
          <label>Recipe</label>
          <RichTextEditor value={bodyHtml} onChange={setBodyHtml} placeholder="Steps, quality notes, tips…" />
          <button type="submit" className="btn btn--primary" disabled={busy}>
            Share to community
          </button>
        </form>
      </section>

      <section className="glass owner-section">
        <h2>Your shared recipes</h2>
        {recipes.length === 0 ? (
          <p className="owner-page__code">No shared recipes yet.</p>
        ) : (
          <ul className="owner-detail-items">
            {recipes.map((r) => (
              <li key={r.id}>
                <strong>{r.title}</strong> — {r.appreciation_count} appreciations · {r.points_earned} pts earned
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="glass owner-section">
        <div className="owner-page__head">
          <h2>City chef rankings</h2>
          <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={onComputeRankings}>
            Refresh rankings
          </button>
        </div>
        {rankings.length === 0 ? (
          <p className="owner-page__code">No rankings yet — tap refresh after you have delivered orders this month.</p>
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
      </section>
    </div>
  );
}
