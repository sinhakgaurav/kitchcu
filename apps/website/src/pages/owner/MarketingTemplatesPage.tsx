import { FormEvent, useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  createMarketingTemplate,
  deleteMarketingTemplate,
  fetchMarketingTemplates,
  sendMarketingTemplate,
  updateMarketingTemplate,
  type MarketingTemplate,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function MarketingTemplatesPage() {
  const { kitchen } = useKitchen();
  const [rows, setRows] = useState<MarketingTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [channel, setChannel] = useState<"whatsapp" | "email">("whatsapp");
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState(
    "Hi {{customer_name}} — today's specials from {{kitchen_name}}: {{menu_line}}. Order on kitchCU!",
  );
  const [audience, setAudience] = useState("all");
  const [sendPreview, setSendPreview] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    try {
      setRows(await fetchMarketingTemplates(kitchen.id));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load templates");
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen) return;
    setBusy(true);
    setError("");
    setOk("");
    try {
      await createMarketingTemplate(kitchen.id, {
        channel,
        name,
        subject: channel === "email" ? subject : null,
        body,
        is_active: true,
      });
      setName("");
      setSubject("");
      setOk("Template saved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onToggle = async (t: MarketingTemplate) => {
    if (!kitchen) return;
    try {
      await updateMarketingTemplate(kitchen.id, t.id, { is_active: !t.is_active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const onDelete = async (id: string) => {
    if (!kitchen) return;
    if (!window.confirm("Delete this template?")) return;
    try {
      await deleteMarketingTemplate(kitchen.id, id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const onSend = async (t: MarketingTemplate, dryRun: boolean) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    setOk("");
    try {
      const res = await sendMarketingTemplate(kitchen.id, t.id, {
        audience,
        dry_run: dryRun,
        sample_vars: { kitchen_name: kitchen.name, menu_line: "chef specials" },
      });
      setSendPreview(res.preview);
      setOk(
        dryRun
          ? `Preview ready — ${res.queued} recipients would be queued.`
          : `Queued ${res.queued} ${res.channel} recipients.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Marketing"
      title="Message templates"
      description="Reusable WhatsApp & email copy for CRM blasts — use {{variables}} for personalization"
    >
      {error && <p className="auth-card__error">{error}</p>}
      {ok && <p className="auth-card__success">{ok}</p>}

      <OwnerPanel title="Create template" description="Saved per kitchen — not platform Meta templates">
        <form className="owner-forms" onSubmit={onCreate}>
          <label>
            Channel
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value as "whatsapp" | "email")}
            >
              <option value="whatsapp">WhatsApp</option>
              <option value="email">Email</option>
            </select>
          </label>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Daily specials" />
          </label>
          {channel === "email" && (
            <label>
              Subject
              <input value={subject} onChange={(e) => setSubject(e.target.value)} required placeholder="Today at our kitchen" />
            </label>
          )}
          <label>
            Body
            <textarea value={body} onChange={(e) => setBody(e.target.value)} required rows={5} />
          </label>
          <p className="owner-forms__hint">
            Variables: {"{{customer_name}}"}, {"{{kitchen_name}}"}, {"{{menu_line}}"}
          </p>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? "Saving…" : "Save template"}
          </button>
        </form>
      </OwnerPanel>

      <OwnerPanel title="Send to CRM" description="Audience for Preview / Send actions below">
        <label className="owner-forms">
          Audience
          <select value={audience} onChange={(e) => setAudience(e.target.value)}>
            <option value="all">All CRM customers</option>
            <option value="vip">VIP (spend ≥ ₹2000 or vip tag)</option>
            <option value="repeat">Repeat (2+ orders)</option>
            <option value="churn_risk">Churn risk tag</option>
          </select>
        </label>
        {sendPreview && (
          <pre className="report-hint" style={{ whiteSpace: "pre-wrap", marginTop: "0.75rem" }}>
            {sendPreview}
          </pre>
        )}
      </OwnerPanel>

      <OwnerPanel title="Your templates" description={`${rows.length} saved`}>
        {loading ? (
          <p className="app-loading">Loading…</p>
        ) : rows.length === 0 ? (
          <OwnerEmpty message="No templates yet — create WhatsApp or email copy above." />
        ) : (
          <ul className="report-rank">
            {rows.map((t) => (
              <li key={t.id}>
                <div className="report-rank__row">
                  <span>
                    <strong>{t.name}</strong>
                    <span className="report-rank__meta">
                      {" "}
                      · {t.channel}
                      {!t.is_active ? " · inactive" : ""}
                      {t.variables.length ? ` · ${t.variables.join(", ")}` : ""}
                    </span>
                  </span>
                  <div className="golden-day-card__actions">
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      disabled={busy || !t.is_active}
                      onClick={() => onSend(t, true)}
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      disabled={busy || !t.is_active}
                      onClick={() => {
                        if (window.confirm(`Send “${t.name}” to ${audience}?`)) onSend(t, false);
                      }}
                    >
                      Send
                    </button>
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => onToggle(t)}>
                      {t.is_active ? "Disable" : "Enable"}
                    </button>
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => onDelete(t.id)}>
                      Delete
                    </button>
                  </div>
                </div>
                {t.subject && <p className="report-hint">Subject: {t.subject}</p>}
                <p className="report-hint">{t.body}</p>
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
