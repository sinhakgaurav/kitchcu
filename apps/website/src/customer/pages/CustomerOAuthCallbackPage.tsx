import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { APP_STORAGE_PREFIX } from "../../shared/brand";
import { completeCustomerOAuth, customerOAuthRedirectUri } from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";

const OAUTH_PROVIDERS = ["google", "facebook", "instagram", "twitter"] as const;

function resolveProvider(): string | null {
  for (const p of OAUTH_PROVIDERS) {
    const raw = sessionStorage.getItem(`${APP_STORAGE_PREFIX}_oauth_pending_${p}`);
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as { provider?: string };
        return parsed.provider ?? p;
      } catch {
        return p;
      }
    }
  }
  return null;
}

export function CustomerOAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { applyAuthResult } = useCustomerAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    const provider = resolveProvider();

    if (!provider || !state || !code) {
      setError("Missing OAuth provider, state, or authorization code");
      return;
    }

    const redirect_uri = customerOAuthRedirectUri();

    completeCustomerOAuth(provider, { code, state, redirect_uri })
      .then((result) => {
        sessionStorage.removeItem(`${APP_STORAGE_PREFIX}_oauth_pending_${provider}`);
        applyAuthResult(result);
        navigate("/", { replace: true });
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "OAuth sign in failed");
      });
  }, [params, navigate, applyAuthResult]);

  if (error) {
    return (
      <div className="auth-page auth-page--customer">
        <div className="auth-card glass" style={{ margin: "4rem auto", maxWidth: 420 }}>
          <h2>Sign in failed</h2>
          <p className="auth-card__error">{error}</p>
          <Link to="/login" className="btn btn--primary">
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page auth-page--customer">
      <div className="auth-card glass" style={{ margin: "4rem auto", maxWidth: 420 }}>
        <p>Completing sign in…</p>
      </div>
    </div>
  );
}
