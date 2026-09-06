import { useTranslation } from "react-i18next";
import { ADMIN_HOST } from "../shared/brand";
import { adminLoginDefaults, DEMO_ADMIN } from "../shared/demo";
import { showDemoCredentials } from "../shared/env";
import { adminUrl } from "../shared/urls";

type LinkProps = {
  className?: string;
  onClick?: () => void;
};

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
 * Shown on login screens only. Dev/QA hosts print the seeded password;
 * production names the email and where the secret lives — never the secret.
 */
export function SuperAdminCredentials() {
  const { t } = useTranslation();
  const defaults = adminLoginDefaults();
  const demo = showDemoCredentials();

  return (
    <details className="auth-card__demo auth-card__demo--admin" open={demo}>
      <summary>{t("common.adminCredentialsTitle")}</summary>
      <p className="auth-card__demo-otp">
        {demo ? (
          <>
            {t("common.adminCredentialsDev", {
              email: DEMO_ADMIN.email,
              password: DEMO_ADMIN.password,
            })}
          </>
        ) : (
          <>
            {t("common.adminCredentialsProd", { email: defaults.email })}
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
