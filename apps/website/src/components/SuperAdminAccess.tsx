import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ADMIN_HOST } from "../shared/brand";
import { adminLoginDefaults, DEMO_ADMIN } from "../shared/demo";
import { showDemoCredentials } from "../shared/env";
import { apiHeaders } from "../shared/http";
import { adminUrl } from "../shared/urls";

type LinkProps = {
  className?: string;
  onClick?: () => void;
};

type CredsProps = {
  className?: string;
};

type LoginHint = {
  email: string;
  password: string | null;
  revealed: boolean;
};

async function fetchAdminLoginHint(): Promise<LoginHint | null> {
  try {
    const res = await fetch("/api/v1/admin/auth/login-hint", { headers: apiHeaders() });
    if (!res.ok) return null;
    return (await res.json()) as LoginHint;
  } catch {
    return null;
  }
}

/** Cross-app entry to the platform console — used on every public home. */
export function SuperAdminLink({ className, onClick }: LinkProps) {
  const { t } = useTranslation();
  return (
    <a
      href={adminUrl("/")}
      className={className}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
    >
      {t("common.adminLogin")}
    </a>
  );
}

/**
 * Login / portal credential strip. Prints the password when identity
 * `ADMIN_LOGIN_REVEAL_PASSWORD=1` (GCP demo) or on non-production hosts.
 */
export function SuperAdminCredentials({ className }: CredsProps) {
  const { t } = useTranslation();
  const defaults = adminLoginDefaults();
  const demo = showDemoCredentials();
  const [hint, setHint] = useState<LoginHint | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchAdminLoginHint().then((next) => {
      if (!cancelled && next) setHint(next);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const email = hint?.email || defaults.email;
  const password =
    hint?.revealed && hint.password
      ? hint.password
      : demo
        ? DEMO_ADMIN.password
        : null;
  const showPassword = Boolean(password);

  return (
    <details className={`auth-card__demo auth-card__demo--admin ${className ?? ""}`.trim()} open={showPassword}>
      <summary>{t("common.adminCredentialsTitle")}</summary>
      <p className="auth-card__demo-otp">
        {showPassword ? (
          <>
            {t("common.adminCredentialsRevealed", {
              email,
              password,
            })}
          </>
        ) : (
          <>
            {t("common.adminCredentialsProd", { email })}
          </>
        )}
      </p>
      <p className="auth-card__demo-note">
        {t("common.adminCredentialsHost", { host: ADMIN_HOST })}{" "}
        <a href={adminUrl("/")} target="_blank" rel="noopener noreferrer">
          {t("common.adminOpenConsole")} →
        </a>
      </p>
    </details>
  );
}
