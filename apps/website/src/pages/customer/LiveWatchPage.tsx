import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchLiveShowcase,
  fetchViewerToken,
  type LiveShowcase,
} from "../../shared/api";

export function LiveWatchPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [error, setError] = useState("");
  const [tokenInfo, setTokenInfo] = useState<{
    room_name: string;
    livekit_url: string | null;
    token: string | null;
    kitchen_name: string | null;
  } | null>(null);
  const [showcase, setShowcase] = useState<LiveShowcase | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const [tok, show] = await Promise.all([
          fetchViewerToken(sessionId),
          fetchLiveShowcase(sessionId).catch(() => null),
        ]);
        if (cancelled) return;
        setTokenInfo({
          room_name: tok.room_name,
          livekit_url: tok.livekit_url,
          token: tok.token,
          kitchen_name: tok.kitchen_name,
        });
        setShowcase(show);
        setError("");
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not join live session");
      }
    })();
    const t = window.setInterval(() => {
      if (!sessionId) return;
      fetchLiveShowcase(sessionId)
        .then((s) => {
          if (!cancelled) setShowcase(s);
        })
        .catch(() => undefined);
    }, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="container" style={{ padding: "2rem 1rem" }}>
        <p className="auth-card__error">Missing session.</p>
        <Link to="/">Back to discovery</Link>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: "2rem 1rem", maxWidth: 720 }}>
      <p className="section__eyebrow">Live now</p>
      <h1 style={{ marginTop: 0 }}>{tokenInfo?.kitchen_name || "Kitchen live"}</h1>
      <p className="owner-muted">
        Watch prep as the kitchen moves through ingredients → prep → prepared.
      </p>
      {error && <p className="auth-card__error">{error}</p>}

      <div className="glass" style={{ padding: "1.25rem", marginBottom: "1.25rem" }}>
        <strong>Phase:</strong>{" "}
        {showcase?.showcase_phase || tokenInfo ? showcase?.showcase_phase || "live" : "…"}
        {showcase?.dish_name ? ` · ${showcase.dish_name}` : ""}
        {tokenInfo?.livekit_url && tokenInfo.token ? (
          <p className="report-hint" style={{ marginTop: "0.75rem" }}>
            LiveKit room <code>{tokenInfo.room_name}</code> — connect with your viewer client using the
            session token (embedded player ships next). URL: {tokenInfo.livekit_url}
          </p>
        ) : (
          <p className="report-hint" style={{ marginTop: "0.75rem" }}>
            Showcase mode — LiveKit media not configured; follow the dish phases below.
          </p>
        )}
      </div>

      {showcase?.showcase_phase === "ingredients" && (
        <ul className="stream-showcase-list">
          {(showcase.ingredients || []).map((ing, i) => (
            <li key={i}>
              {ing.ingredient_name}
              {ing.quantity != null ? ` — ${ing.quantity}${ing.unit ? ` ${ing.unit}` : ""}` : ""}
            </li>
          ))}
        </ul>
      )}
      {showcase?.showcase_phase === "prep" && (
        <ol className="stream-showcase-list">
          {(showcase.prep_steps || []).map((step) => (
            <li
              key={step.step_order}
              className={
                showcase.active_prep_step_order === step.step_order ? "stream-phase-btn active" : ""
              }
            >
              {step.title || step.body_html?.replace(/<[^>]+>/g, "") || `Step ${step.step_order}`}
            </li>
          ))}
        </ol>
      )}
      {showcase?.showcase_phase === "prepared" && (
        <p className="stream-prepared-banner">Dish marked prepared — order while it&apos;s hot.</p>
      )}

      <p style={{ marginTop: "1.5rem" }}>
        <Link className="btn btn--primary" to="/">
          Find more kitchens
        </Link>
      </p>
    </div>
  );
}
