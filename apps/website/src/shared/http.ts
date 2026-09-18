/** Shared HTTP helpers — correlation IDs for gateway observability. */

import { APP_STORAGE_PREFIX } from "./brand";

export function nextCorrelationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `corr-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function correlationHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    "X-Correlation-ID": nextCorrelationId(),
    ...(extra ?? {}),
  };
}

/** Base headers for JSON API calls through the gateway edge. */
export function apiHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...correlationHeaders(extra),
  };
}

/** FastAPI `detail` may be a string or a validation-error list — never show a blank failure. */
export function formatApiDetail(detail: unknown, fallback = "Request failed"): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const rec = item as { msg?: unknown; loc?: unknown };
        const msg = typeof rec.msg === "string" ? rec.msg : "";
        const loc = Array.isArray(rec.loc)
          ? rec.loc.filter((part) => part !== "body" && part !== "query").join(".")
          : "";
        return loc && msg ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}

/** Prefix for optional client-side correlation debugging (not sent to server). */
export const CORRELATION_STORAGE_KEY = `${APP_STORAGE_PREFIX}_last_correlation_id`;
