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

/** Prefix for optional client-side correlation debugging (not sent to server). */
export const CORRELATION_STORAGE_KEY = `${APP_STORAGE_PREFIX}_last_correlation_id`;
