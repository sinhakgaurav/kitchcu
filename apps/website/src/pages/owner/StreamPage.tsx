import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LiveKitViewer } from "../../components/LiveKitViewer";
import { LocalCameraPreview } from "../../components/LocalCameraPreview";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  endKitchenStream,
  fetchLiveKitchens,
  fetchLiveShowcase,
  fetchMenu,
  fetchStreamSession,
  fetchStreamSettings,
  goKitchenLive,
  updateStreamSettings,
  updateStreamShowcase,
  type LiveKitchenSummary,
  type LiveSession,
  type LiveShowcase,
  type ShowcasePhase,
  type StreamSettings,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

type PublishCreds = { url: string; token: string };

/** Keep publisher credentials stable — showcase PATCH re-issues a new JWT and remounting kills the camera. */
function mergeSessionKeepPublish(
  prev: LiveSession | null,
  next: LiveSession,
): LiveSession {
  return {
    ...next,
    publisher_token: prev?.publisher_token ?? next.publisher_token,
    livekit_url: prev?.livekit_url ?? next.livekit_url,
  };
}

const PHASES: { id: ShowcasePhase; label: string; hint: string }[] = [
  { id: "ingredients", label: "Ingredients", hint: "Showcase what's going into the dish" },
  { id: "prep", label: "Prep", hint: "Walk customers through prep steps" },
  { id: "prepared", label: "Prepared", hint: "Mark the dish ready — golden moment" },
];

export function StreamPage() {
  const { kitchen } = useKitchen();
  const [settings, setSettings] = useState<StreamSettings | null>(null);
  const [session, setSession] = useState<LiveSession | null>(null);
  const [showcase, setShowcase] = useState<LiveShowcase | null>(null);
  const [liveKitchens, setLiveKitchens] = useState<LiveKitchenSummary[]>([]);
  const [dishes, setDishes] = useState<{ id: string; name: string }[]>([]);
  const [title, setTitle] = useState("Live kitchen prep");
  const [dishId, setDishId] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  /** Stable LiveKit publish creds for the active session (do not refresh on phase changes). */
  const [publishCreds, setPublishCreds] = useState<PublishCreds | null>(null);

  const rememberPublishCreds = (s: LiveSession | null) => {
    if (s?.status === "live" && s.publisher_token && s.livekit_url) {
      setPublishCreds((prev) => prev ?? { url: s.livekit_url!, token: s.publisher_token! });
    }
  };

  const loadShowcase = async (sessionId: string) => {
    try {
      setShowcase(await fetchLiveShowcase(sessionId));
    } catch {
      setShowcase(null);
    }
  };

  const load = async () => {
    if (!kitchen) return;
    try {
      const [settingsRes, sessionRes, liveRes, menu] = await Promise.all([
        fetchStreamSettings(kitchen.id),
        fetchStreamSession(kitchen.id),
        fetchLiveKitchens(),
        fetchMenu(kitchen.id),
      ]);
      setSettings(settingsRes);
      setSession(sessionRes);
      setLiveKitchens(liveRes.kitchens);
      setDishes(menu.dishes.filter((d) => d.is_active).map((d) => ({ id: d.id, name: d.name })));
      if (sessionRes?.status === "live") {
        rememberPublishCreds(sessionRes);
        await loadShowcase(sessionRes.id);
        if (sessionRes.dish_id) setDishId(sessionRes.dish_id);
      } else {
        setPublishCreds(null);
        setShowcase(null);
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stream settings");
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const onToggleSharing = async (enabled: boolean) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const res = await updateStreamSettings(kitchen.id, { live_sharing_enabled: enabled });
      setSettings(res);
      setMsg(enabled ? "Live sharing enabled — pick a dish and go live." : "Live sharing disabled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update settings");
    } finally {
      setBusy(false);
    }
  };

  const onGoLive = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen) return;
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const res = await goKitchenLive(kitchen.id, {
        title: title.trim() || "Live kitchen prep",
        dish_id: dishId || undefined,
        showcase_phase: dishId ? "ingredients" : undefined,
      });
      setSession(res);
      rememberPublishCreds(res);
      if (res?.id) await loadShowcase(res.id);
      setMsg(
        dishId
          ? "You are live — camera preview below. Switch dish phases as you cook."
          : "You are live — allow camera when prompted. Feature a dish to show prep phases.",
      );
      // Do not full reload / swap publisher token — remounting LiveKit kills the camera mid-stream.
    } catch (err) {
      setError(err instanceof Error ? err.message : "Go live failed");
    } finally {
      setBusy(false);
    }
  };

  const onEndLive = async () => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      await endKitchenStream(kitchen.id);
      setSession(null);
      setShowcase(null);
      setPublishCreds(null);
      setMsg("Stream ended.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "End stream failed");
    } finally {
      setBusy(false);
    }
  };

  const onFeatureDish = async () => {
    if (!kitchen || !dishId) return;
    setBusy(true);
    setError("");
    try {
      const res = await updateStreamShowcase(kitchen.id, {
        dish_id: dishId,
        showcase_phase: "ingredients",
      });
      setSession((prev) => mergeSessionKeepPublish(prev, res));
      await loadShowcase(res.id);
      setMsg(`Featuring ${res.dish_name} — ingredients showcase.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not feature dish");
    } finally {
      setBusy(false);
    }
  };

  const onSetPhase = async (phase: ShowcasePhase) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const res = await updateStreamShowcase(kitchen.id, {
        showcase_phase: phase,
        active_prep_step_order: phase === "prep" ? 1 : undefined,
      });
      setSession((prev) => mergeSessionKeepPublish(prev, res));
      await loadShowcase(res.id);
      setMsg(`Showcase → ${phase}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update phase");
    } finally {
      setBusy(false);
    }
  };

  const onPrepStep = async (stepOrder: number) => {
    if (!kitchen) return;
    setBusy(true);
    try {
      const res = await updateStreamShowcase(kitchen.id, {
        showcase_phase: "prep",
        active_prep_step_order: stepOrder,
      });
      setSession((prev) => mergeSessionKeepPublish(prev, res));
      await loadShowcase(res.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not advance prep step");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return <p className="app-loading">Select a kitchen…</p>;

  const isLive = session?.status === "live";

  return (
    <OwnerPageShell
      eyebrow="Engagement"
      title="Live streaming"
      description="Go live per dish — showcase ingredients, walk prep steps, mark prepared (F46–F47)."
    >
      {error && <div className="auth-card__error">{error}</div>}
      {msg && <div className="auth-card__success">{msg}</div>}

      <OwnerPanel title="Sharing settings">
        {settings && (
          <div className="stream-settings">
            <label className="stream-settings__toggle">
              <input
                type="checkbox"
                checked={settings.live_sharing_enabled}
                disabled={busy || settings.is_live}
                onChange={(e) => onToggleSharing(e.target.checked)}
              />
              Allow live kitchen sharing
            </label>
            <label className="stream-settings__toggle">
              <input
                type="checkbox"
                checked={settings.q_and_a_enabled}
                disabled={busy}
                onChange={async (e) => {
                  if (!kitchen) return;
                  setBusy(true);
                  try {
                    const res = await updateStreamSettings(kitchen.id, {
                      q_and_a_enabled: e.target.checked,
                    });
                    setSettings(res);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Update failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              />
              Q&amp;A during live sessions
            </label>
            <p className="stream-settings__meta">
              LiveKit: {settings.livekit_configured ? "configured" : "not configured (dev mode — no camera token)"}
              {settings.is_live && <span className="stream-settings__live-badge"> · LIVE NOW</span>}
            </p>
          </div>
        )}
      </OwnerPanel>

      <OwnerPanel title="Go live with a dish">
        {isLive ? (
          <div className="stream-live">
            <p>
              <strong>{session.title}</strong> — room <code>{session.room_name}</code>
            </p>
            <p>Viewers joined: {session.viewer_count}</p>
            {session.dish_name && (
              <p>
                Featuring <strong>{session.dish_name}</strong>
                <span className={`stream-phase stream-phase--${session.showcase_phase}`}>
                  {" "}
                  · {session.showcase_phase}
                </span>
              </p>
            )}
            <div className="stream-live__preview">
              {publishCreds ? (
                <>
                  <LiveKitViewer url={publishCreds.url} token={publishCreds.token} publish />
                  <p className="stream-live__hint">
                    Camera publishing to LiveKit — customers can Watch live. Phase changes keep this preview
                    running.
                  </p>
                </>
              ) : (
                <>
                  <LocalCameraPreview />
                  <p className="stream-live__hint">
                    Local camera preview (LiveKit not configured). Dish showcase still updates for customers;
                    wire LiveKit in admin Control to broadcast video.
                  </p>
                </>
              )}
            </div>

            <div className="stream-dish-pick">
              <label>
                Feature dish
                <select
                  value={dishId}
                  onChange={(e) => setDishId(e.target.value)}
                  disabled={busy}
                >
                  <option value="">Select dish…</option>
                  {dishes.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={busy || !dishId}
                onClick={onFeatureDish}
              >
                Load showcase
              </button>
              {dishes.length === 0 && (
                <p className="owner-muted">
                  No dishes yet — <Link to="/dashboard/menu/new">add a dish</Link> with recipe first.
                </p>
              )}
            </div>

            {session.dish_id && (
              <>
                <div className="stream-phase-bar">
                  {PHASES.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className={`stream-phase-btn ${session.showcase_phase === p.id ? "active" : ""}`}
                      disabled={busy}
                      title={p.hint}
                      onClick={() => onSetPhase(p.id)}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                {showcase && session.showcase_phase === "ingredients" && (
                  <ul className="stream-showcase-list">
                    {showcase.ingredients.map((ing, i) => (
                      <li key={`${ing.ingredient_name}-${i}`}>
                        <strong>{ing.ingredient_name}</strong>
                        <span>
                          {ing.quantity}
                          {ing.unit}
                        </span>
                      </li>
                    ))}
                    {showcase.ingredients.length === 0 && (
                      <li className="owner-muted">
                        No recipe lines — add them under{" "}
                        <Link to={`/dashboard/ingredients?dish=${session.dish_id}`}>Recipe & prep</Link>.
                      </li>
                    )}
                  </ul>
                )}

                {showcase && session.showcase_phase === "prep" && (
                  <ul className="stream-showcase-list">
                    {showcase.prep_steps.map((step) => (
                      <li key={step.step_order}>
                        <button
                          type="button"
                          className={`stream-step ${
                            session.active_prep_step_order === step.step_order ? "active" : ""
                          }`}
                          disabled={busy}
                          onClick={() => onPrepStep(step.step_order)}
                        >
                          <strong>
                            Step {step.step_order}
                            {step.title ? `: ${step.title}` : ""}
                          </strong>
                          {step.duration_min != null && <span>{step.duration_min}m</span>}
                        </button>
                      </li>
                    ))}
                    {showcase.prep_steps.length === 0 && (
                      <li className="owner-muted">No prep steps on this dish recipe yet.</li>
                    )}
                  </ul>
                )}

                {session.showcase_phase === "prepared" && (
                  <p className="stream-prepared-banner">
                    Dish marked prepared
                    {session.prepared_at
                      ? ` · ${new Date(session.prepared_at).toLocaleTimeString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}`
                      : ""}
                  </p>
                )}
              </>
            )}

            <button type="button" className="btn btn--danger" disabled={busy} onClick={onEndLive}>
              End stream
            </button>
          </div>
        ) : (
          <form className="stream-go-live" onSubmit={onGoLive}>
            <label>
              Stream title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={255}
                disabled={busy || !settings?.live_sharing_enabled}
              />
            </label>
            <label>
              Dish to feature
              <select
                value={dishId}
                onChange={(e) => setDishId(e.target.value)}
                disabled={busy || !settings?.live_sharing_enabled}
              >
                <option value="">Kitchen-only (feature dish later)</option>
                {dishes.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <p className="owner-forms__hint">
              Starts on <strong>ingredients</strong> showcase when a dish is selected — then move to
              prep steps and mark prepared.
            </p>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy || !settings?.live_sharing_enabled}
            >
              Go live
            </button>
          </form>
        )}
      </OwnerPanel>

      <OwnerPanel title="Kitchens live now" description="Other kitchens broadcasting on kitchCU">
        {liveKitchens.length === 0 ? (
          <p className="owner-muted">No kitchens are streaming right now.</p>
        ) : (
          <ul className="stream-live-list">
            {liveKitchens.map((k) => (
              <li key={k.session_id}>
                <strong>{k.kitchen_name}</strong> ({k.kitchen_code}) — {k.title}
                {k.dish_name && (
                  <span className="stream-live-list__dish">
                    {" "}
                    · {k.dish_name}
                    {k.showcase_phase && k.showcase_phase !== "idle"
                      ? ` (${k.showcase_phase})`
                      : ""}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
