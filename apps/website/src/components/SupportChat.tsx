import { FormEvent, useEffect, useRef, useState } from "react";
import { CUSTOMER_GREETING, OWNER_GREETING } from "../lib/supportChat";
import {
  createSupportTicket,
  sendSupportChat,
  type ChatAudience,
  type TicketCategory,
} from "../lib/supportApi";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

function greeting(audience: ChatAudience): Message {
  return {
    id: "greeting",
    role: "assistant",
    content: audience === "owner" ? OWNER_GREETING : CUSTOMER_GREETING,
  };
}

const CATEGORIES: { value: TicketCategory; label: string }[] = [
  { value: "order_issue", label: "Order issue" },
  { value: "delivery", label: "Delivery" },
  { value: "quality", label: "Food quality" },
  { value: "billing", label: "Billing" },
  { value: "technical", label: "Technical" },
  { value: "complaint", label: "Complaint" },
  { value: "general", label: "General" },
];

export function SupportChat() {
  const [open, setOpen] = useState(false);
  const [audience, setAudience] = useState<ChatAudience>("owner");
  const [messages, setMessages] = useState<Message[]>([greeting("owner")]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [suggestTicket, setSuggestTicket] = useState(false);
  const [suggestedCategory, setSuggestedCategory] = useState<TicketCategory>("general");
  const [showTicketForm, setShowTicketForm] = useState(false);
  const [ticketDone, setTicketDone] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, open, showTicketForm]);

  const switchAudience = (next: ChatAudience) => {
    if (next === audience) return;
    setAudience(next);
    setMessages([greeting(next)]);
    setError("");
    setSuggestTicket(false);
    setShowTicketForm(false);
    setTicketDone(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    const userMsg: Message = { id: `u-${Date.now()}`, role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setError("");
    setBusy(true);

    try {
      const res = await sendSupportChat(
        audience,
        text,
        nextMessages.map((m) => ({ role: m.role, content: m.content })),
      );
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: "assistant", content: res.reply },
      ]);
      setSuggestTicket(res.suggest_ticket);
      if (res.suggested_category) {
        setSuggestedCategory(res.suggested_category as TicketCategory);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    } finally {
      setBusy(false);
    }
  };

  const handleTicketSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    try {
      const ticket = await createSupportTicket({
        audience,
        category: (fd.get("category") as TicketCategory) || suggestedCategory,
        subject: String(fd.get("subject")),
        description: String(fd.get("description")),
        customer_name: String(fd.get("name") || "") || undefined,
        customer_phone: String(fd.get("phone") || "") || undefined,
        customer_email: String(fd.get("email") || "") || undefined,
        order_code: String(fd.get("order_code") || "") || undefined,
        chat_history: messages
          .filter((m) => m.id !== "greeting")
          .map((m) => ({ role: m.role, content: m.content })),
      });
      setTicketDone(ticket.ticket_number);
      setShowTicketForm(false);
      setSuggestTicket(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          content: `Support ticket ${ticket.ticket_number} created. Our team will respond within 24 hours on weekdays.`,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setBusy(false);
    }
    if (!lastUser) return;
  };

  return (
    <>
      <button
        type="button"
        className={`support-chat__launcher ${open ? "support-chat__launcher--open" : ""}`}
        aria-label={open ? "Close support chat" : "Open support chat"}
        onClick={() => setOpen(!open)}
      >
        {open ? "✕" : "💬"}
        {!open && <span className="support-chat__launcher-label">AI Support</span>}
      </button>

      {open && (
        <div className="support-chat glass" role="dialog" aria-label="kitchCU support chat">
          <header className="support-chat__head">
            <div>
              <strong>kitchCU Support</strong>
              <span>AI assistant · raise tickets for order issues</span>
            </div>
            <button type="button" className="support-chat__close" onClick={() => setOpen(false)} aria-label="Close">
              ✕
            </button>
          </header>

          <div className="support-chat__tabs">
            <button type="button" className={audience === "owner" ? "active" : ""} onClick={() => switchAudience("owner")}>
              Owner support
            </button>
            <button type="button" className={audience === "customer" ? "active" : ""} onClick={() => switchAudience("customer")}>
              Customer support
            </button>
          </div>

          <div className="support-chat__messages" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`support-chat__msg support-chat__msg--${m.role}`}>
                {m.content.split("\n").map((line, i) => (
                  <p key={i}>{line.replace(/\*\*(.*?)\*\*/g, "$1")}</p>
                ))}
              </div>
            ))}
            {busy && !showTicketForm && <div className="support-chat__typing">Thinking...</div>}
          </div>

          {(suggestTicket || ticketDone) && !showTicketForm && (
            <div className="support-chat__ticket-cta">
              {ticketDone ? (
                <span>Ticket {ticketDone} logged ✓</span>
              ) : (
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setShowTicketForm(true)}>
                  Raise support ticket
                </button>
              )}
            </div>
          )}

          {showTicketForm && (
            <form className="support-chat__ticket-form" onSubmit={handleTicketSubmit}>
              <h4>Raise support ticket</h4>
              <label>
                Category
                <select name="category" defaultValue={suggestedCategory}>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Subject
                <input name="subject" required placeholder="Brief summary" defaultValue={messages.filter(m => m.role === "user").at(-1)?.content.slice(0, 80)} />
              </label>
              <label>
                Details
                <textarea name="description" required rows={3} placeholder="Describe the issue..." />
              </label>
              <label>
                Order code (if order-related)
                <input name="order_code" placeholder="CKPNQ001-BILL-..." />
              </label>
              <label>
                Your name
                <input name="name" placeholder="Optional" />
              </label>
              <label>
                Phone
                <input name="phone" placeholder="+91..." />
              </label>
              <label>
                Email
                <input name="email" type="email" placeholder="Optional" />
              </label>
              <div className="support-chat__ticket-actions">
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowTicketForm(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>Submit ticket</button>
              </div>
            </form>
          )}

          {error && <div className="support-chat__error">{error}</div>}

          {!showTicketForm && (
            <form className="support-chat__form" onSubmit={handleSubmit}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={audience === "owner" ? "Ask about pricing, WhatsApp orders..." : "Order issue? Describe here..."}
                disabled={busy}
                maxLength={500}
              />
              <button type="submit" className="btn btn--primary btn--sm" disabled={busy || !input.trim()}>
                Send
              </button>
            </form>
          )}
        </div>
      )}
    </>
  );
}
