/** Presentation helpers for customer PWA surfaces (no PII logging). */

export function customerInitials(name: string | null | undefined): string {
  const parts = (name ?? "")
    .trim()
    .split(/\s+/)
    .filter((part) => /\p{L}/u.test(part));
  if (!parts.length) return "K";
  const first = parts[0][0] ?? "K";
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? "") : (parts[0][1] ?? "");
  return `${first}${last}`.toUpperCase();
}

/** Own-profile display: country code + last 4 digits. */
export function maskCustomerPhone(phone: string | null | undefined): string {
  if (!phone) return "";
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 4) return phone;
  const last = digits.slice(-4);
  const cc = digits.length > 10 ? digits.slice(0, digits.length - 10) : "91";
  return `+${cc} •••• ${last}`;
}

export function customerStatusTone(status: string): "ok" | "live" | "bad" | "muted" {
  const s = status.toLowerCase();
  if (s === "delivered" || s === "completed" || s === "resolved") return "ok";
  if (s === "cancelled" || s === "failed" || s === "rejected") return "bad";
  if (
    s === "received" ||
    s === "accepted" ||
    s === "preparing" ||
    s === "ready" ||
    s === "out_for_delivery" ||
    s === "pending"
  ) {
    return "live";
  }
  return "muted";
}

export function humanStatus(status: string): string {
  return status.replace(/_/g, " ");
}
