import { useEffect, useState } from "react";
import {
  endKitchenStream,
  fetchLiveKitchens,
  fetchStreamSession,
  fetchStreamSettings,
  goKitchenLive,
  updateStreamSettings,
  type LiveKitchenSummary,
  type LiveSession,
  type StreamSettings,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function StreamPage() {
  const { kitchen } = useKitchen();
  const [settings, setSettings] = useState<StreamSettings | null>(null);
  const [session, setSession] = useState<LiveSession | null>(null);
  const [liveKitchens, setLiveKitchens] = useState<LiveKitchenSummary[]>([]);
  const [title, setTitle] = useState("Live kitchen prep");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!kitchen) return;
    try {
      const [settingsRes, sessionRes, liveRes] = await Promise.all([
        fetchStreamSettings(kitchen.id),
        fetchStreamSession(kitchen.id),
        fetchLiveKitchens(),
      ]);
      setSettings(settingsRes);
      setSession(sessionRes);
      setLiveKitchens(liveRes.kitchens);
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
      setMsg(enabled ? "Live sharing enabled — you can go live when ready." : "Live sharing disabled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update settings");
    } finally {
      setBusy(false);
    }
  };

  const onGoLive = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen) return;
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const res = await goKitchenLive(kitchen.id, { title: title.trim() || "Live kitchen prep" });
      setSession(res);
      setMsg("You are live. Connect your camera via LiveKit when configured.");
      await load();
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
      setMsg("Stream ended.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "End stream failed");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return <p className="app-loading">Select a kitchen…</p>;

  return (
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Live streaming</h1>
          <p>Opt in to share live prep with customers (F47). Enterprise kitchens can broadcast via LiveKit.</p>
        </div>
      </header>

      {error && <div className="auth-card__error">{error}</div>}
      {msg && <div className="auth-card__success">{msg}</div>}

      <section className="glass owner-page__section">
        <h2>Sharing settings</h2>
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
      </section>

      <section className="glass owner-page__section">
        <h2>Go live</h2>
        {session?.status === "live" ? (
          <div className="stream-live">
            <p><strong>{session.title}</strong> — room <code>{session.room_name}</code></p>
            <p>Viewers joined: {session.viewer_count}</p>
            {session.publisher_token && (
              <p className="stream-live__hint">Publisher token issued — connect your LiveKit client.</p>
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
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy || !settings?.live_sharing_enabled}
            >
              Go live
            </button>
          </form>
        )}
      </section>

      <section className="glass owner-page__section">
        <h2>Kitchens live now</h2>
        {liveKitchens.length === 0 ? (
          <p>No kitchens are streaming right now.</p>
        ) : (
          <ul className="stream-live-list">
            {liveKitchens.map((k) => (
              <li key={k.session_id}>
                <strong>{k.kitchen_name}</strong> ({k.kitchen_code}) — {k.title}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
