import { useCallback, useState } from "react";
import {
  loginWithCustomerOAuthProvider,
  requestCustomerWhatsAppOtp,
  verifyCustomerWhatsAppOtp,
  type CustomerAuthResult,
  type OAuthProvider,
} from "../shared/customerApi";
import { normalizePhone } from "../shared/api";

type Props = {
  onSuccess: () => void | Promise<void>;
  onAuth: (result: CustomerAuthResult) => void | Promise<void>;
  onError: (message: string) => void;
  /** Required for new customer signup / social continue */
  policiesAgreed?: boolean;
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
}: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [whatsappPhone, setWhatsappPhone] = useState("");
  const [whatsappOtp, setWhatsappOtp] = useState("");
  const [whatsappStep, setWhatsappStep] = useState<"idle" | "otp">("idle");

  const providers: OAuthProvider[] = [
    { id: "google", label: "Google" },
    { id: "facebook", label: "Facebook" },
    { id: "instagram", label: "Instagram" },
    { id: "twitter", label: "Twitter / X" },
    { id: "whatsapp", label: "WhatsApp", method: "otp" },
  ];

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
        const result = await loginWithCustomerOAuthProvider(provider);
        await onAuth(result);
        await onSuccess();
      } catch (err) {
        onError(err instanceof Error ? err.message : "Sign in failed");
      } finally {
        setBusy(null);
      }
    },
    [onSuccess, onAuth, onError, ensurePolicies],
  );

  const handleWhatsAppRequest = async () => {
    if (!ensurePolicies()) return;
    setBusy("whatsapp");
    try {
      await requestCustomerWhatsAppOtp(normalizePhone(whatsappPhone));
      setWhatsappStep("otp");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not send OTP");
    } finally {
      setBusy(null);
    }
  };

  const handleWhatsAppVerify = async () => {
    if (!ensurePolicies()) return;
    setBusy("whatsapp");
    try {
      const result = await verifyCustomerWhatsAppOtp(normalizePhone(whatsappPhone), whatsappOtp);
      await onAuth(result);
      await onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="customer-social-login">
      <p className="customer-social-login__label">Or continue with</p>
      <div className="customer-social-login__grid">
        {providers.map((p) =>
          p.method === "otp" ? null : (
            <button
              key={p.id}
              type="button"
              className={`social-btn ${PROVIDER_CLASS[p.id] ?? ""}`}
              disabled={!!busy || !policiesAgreed}
              onClick={() => handleOAuth(p.id)}
            >
              {busy === p.id ? "Connecting…" : PROVIDER_LABELS[p.id]}
            </button>
          ),
        )}
      </div>

      <div className="customer-social-login__whatsapp">
        <p className="auth-card__hint">WhatsApp — sign in with your phone number</p>
        <label>
          Phone
          <input
            value={whatsappPhone}
            onChange={(e) => setWhatsappPhone(e.target.value)}
            placeholder="9876543210"
            disabled={whatsappStep === "otp"}
          />
        </label>
        {whatsappStep === "otp" && (
          <label>
            OTP
            <input
              value={whatsappOtp}
              onChange={(e) => setWhatsappOtp(e.target.value)}
              placeholder="123456"
              maxLength={6}
            />
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
    </div>
  );
}
