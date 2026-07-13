export type ChatAudience = "owner" | "customer";

export type ChatResponse = {
  audience: ChatAudience;
  reply: string;
  source: "knowledge" | "ai";
  suggest_ticket: boolean;
  suggested_category: string | null;
};

export type TicketCategory =
  | "order_issue"
  | "delivery"
  | "quality"
  | "billing"
  | "technical"
  | "complaint"
  | "general";

export type SupportTicket = {
  id: string;
  ticket_number: string;
  audience: string;
  category: string;
  status: string;
  priority: string;
  subject: string;
  description: string;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  order_code: string | null;
  created_at: string;
  messages: { id: string; author_type: string; message: string; created_at: string }[];
};

export async function sendSupportChat(
  audience: ChatAudience,
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
): Promise<ChatResponse> {
  const res = await fetch("/api/v1/support/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audience, message, history: history.slice(-10) }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Chat unavailable");
  return body as ChatResponse;
}

export async function createSupportTicket(data: {
  audience: ChatAudience;
  category: TicketCategory;
  subject: string;
  description: string;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  order_code?: string;
  chat_history?: { role: "user" | "assistant"; content: string }[];
}): Promise<SupportTicket> {
  const res = await fetch("/api/v1/support/tickets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...data, source: "ai_chat" }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Failed to create ticket");
  return body as SupportTicket;
}
