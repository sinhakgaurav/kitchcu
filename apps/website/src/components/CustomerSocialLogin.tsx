import { useCallback, useEffect, useState } from "react";
import {
  fetchOAuthProviders,
  loginWithCustomerOAuthProvider,
  requestCustomerWhatsAppOtp,
  verifyCustomerWhatsAppOtp,
  type CustomerAuthResult,
  type OAuthProvider,
} from "../shared/customerApi";
import { PhoneField } from "./PhoneField";
import {
  otpInputValue,
  toE164,
  validateNationalPhone,
  validateOtp,
} from "../shared/validation";

type Props = {
  onSuccess: () => void | Promise<void>;
  onAuth: (result: CustomerAuthResult) => void | Promise<void>;
  onError: (message: string) => void;
  /** Required for new customer signup / social continue */
  policiesAgreed?: boolean;
  /** Return path after real OAuth redirect (`/oauth/callback`). */
  nextPath?: string;
};

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  facebook: "Facebook",
  instagram: "Instagram",
  twitter: "Twitter / X",
  whatsapp: "WhatsApp",
};

const PROVIDER_CLASS: Record<string, string> = {
  google: "social-btn--google",
  facebook: "social-btn--facebook",
  instagram: "social-btn--instagram",
  twitter: "social-btn--twitter",
  whatsapp: "social-btn--whatsapp",
};

export function CustomerSocialLogin({
  onSuccess,
  onAuth,
  onError,
  policiesAgreed = true,
  nextPath = "/",
}: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [whatsappPhone, setWhatsappPhone] = useState("");
  const [whatsappOtp, setWhatsappOtp] = useState("");
  const [whatsappStep, setWhatsappStep] = useState<"idle" | "otp">("idle");
  const [fieldErrors, setFieldErrors] = useState<{ phone?: string; otp?: string }>({});
  const [providers, setProviders] = useState<OAuthProvider[] | null>(null);

  useEffect(() => {
    fetchOAuthProviders()
      .then(setProviders)
      .catch(() => setProviders([{ id: "whatsapp", label: "WhatsApp", method: "otp" }]));
  }, []);

  const oauthProviders = (providers ?? []).filter((p) => p.id !== "whatsapp" && p.method !== "otp");
  const showWhatsapp =
    !providers || providers.some((p) => p.id === "whatsapp" || p.method === "otp");

  const ensurePolicies = useCallback(() => {
    if (policiesAgreed) return true;
    onError("Please agree to the Terms, Privacy, and Refund Policies to continue.");
    return false;
  }, [policiesAgreed, onError]);

  const handleOAuth = useCallback(
    async (provider: string) => {
      if (!ensurePolicies()) return;
      setBusy(provider);
      try {
        const result = await loginWithCustomerOAuthProvider(provider, { next: nextPath });
        await onAuth(result);
        await onSuccess();
      } catch (err) {
        onError(err instanceof Error ? err.message : "Sign in failed");
      } finally {
        setBusy(null);
      }
    },
    [onSuccess, onAuth, onError, ensurePolicies, nextPath],
  );

  const handleWhatsAppRequest = async () => {
    if (!ensurePolicies()) return;
    const phoneMessage = validateNationalPhone(whatsappPhone);
    setFieldErrors({ phone: phoneMessage ?? undefined });
    if (phoneMessage) {
      onError(phoneMessage);
      return;
    }
    setBusy("whatsapp");
    try {
      await requestCustomerWhatsAppOtp(toE164(whatsappPhone));
      setWhatsappStep("otp");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not send OTP");
    } finally {
      setBusy(null);
    }
  };

  const handleWhatsAppVerify = async () => {
    if (!ensurePolicies()) return;
    const otpMessage = validateOtp(whatsappOtp);
    setFieldErrors({ otp: otpMessage ?? undefined });
    if (otpMessage) {
      onError(otpMessage);
      return;
    }
    setBusy("whatsapp");
    try {
      const result = await verifyCustomerWhatsAppOtp(toE164(whatsappPhone), whatsappOtp);
      await onAuth(result);
      await onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setBusy(null);
    }
  };

  if (!providers) {
    return <p className="auth-card__hint">Loading sign-in options…</p>;
  }

  return (
    <div className="customer-social-login">
      {oauthProviders.length > 0 && (
        <>
          <p className="customer-social-login__label">Or continue with</p>
          <div className="customer-social-login__grid">
            {oauthProviders.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`social-btn ${PROVIDER_CLASS[p.id] ?? ""}`}
                disabled={!!busy || !policiesAgreed}
                onClick={() => handleOAuth(p.id)}
              >
                {busy === p.id ? "Connecting…" : PROVIDER_LABELS[p.id] ?? p.label}
              </button>
            ))}
          </div>
        </>
      )}

      {showWhatsapp && (
      <div className="customer-social-login__whatsapp">
        <p className="auth-card__hint">WhatsApp — sign in with your phone number</p>
        <PhoneField
          label="Phone"
          value={whatsappPhone}
          onChange={(national) => {
            setWhatsappPhone(national);
            setFieldErrors((f) => ({ ...f, phone: undefined }));
          }}
          error={fieldErrors.phone}
          disabled={whatsappStep === "otp"}
        />
        {whatsappStep === "otp" && (
          <label>
            OTP
            <input
              value={whatsappOtp}
              onChange={(e) => {
                setWhatsappOtp(otpInputValue(e.target.value));
                setFieldErrors((f) => ({ ...f, otp: undefined }));
              }}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="123456"
              maxLength={6}
              className={fieldErrors.otp ? "input-invalid" : undefined}
              aria-invalid={Boolean(fieldErrors.otp)}
            />
            {fieldErrors.otp ? <span className="field-error">{fieldErrors.otp}</span> : null}
          </label>
        )}
        <button
          type="button"
          className="btn btn--ghost btn--sm social-btn--whatsapp"
          disabled={!!busy || !whatsappPhone.trim() || !policiesAgreed}
          onClick={whatsappStep === "otp" ? handleWhatsAppVerify : handleWhatsAppRequest}
        >
          {busy === "whatsapp"
            ? "Please wait…"
            : whatsappStep === "otp"
              ? "Verify WhatsApp OTP"
              : "Send WhatsApp OTP"}
        </button>
      </div>
      )}
    </div>
  );
}
