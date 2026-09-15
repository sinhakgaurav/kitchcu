import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { LiveCapturePhotoField } from "../LiveCapturePhotoField";
import {
  updateOwnerKyc,
  uploadOwnerAvatar,
  uploadOwnerLivePhoto,
  type OwnerProfile,
} from "../../shared/api";
import { useKitchenAuth } from "../../shared/kitchenAuth";
import { OwnerPanel } from "./OwnerPageShell";

export function OwnerIdentityPanel() {
  const { t } = useTranslation();
  const { owner, refresh } = useKitchenAuth();
  const [aadhaar, setAadhaar] = useState("");
  const [pan, setPan] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  if (!owner) return null;

  const apply = async (next: OwnerProfile) => {
    await refresh();
    return next;
  };

  const saveIds = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setOk("");
    setBusy(true);
    try {
      const payload: { aadhaar_number?: string; pan_number?: string } = {};
      if (aadhaar.trim()) payload.aadhaar_number = aadhaar.trim();
      if (pan.trim()) payload.pan_number = pan.trim();
      if (!payload.aadhaar_number && !payload.pan_number) {
        setError(t("owner.identity.idsRequired"));
        return;
      }
      await updateOwnerKyc(payload);
      setAadhaar("");
      setPan("");
      await refresh();
      setOk(t("owner.identity.idsSaved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <OwnerPanel title={t("owner.identity.title")} description={t("owner.identity.hint")}>
      <div id="identity" className="owner-identity">
        {error ? <div className="auth-card__error">{error}</div> : null}
        {ok ? <p className="owner-muted" role="status">{ok}</p> : null}
        <p className={`owner-identity__status${owner.kyc_complete ? " owner-identity__status--ok" : ""}`}>
          {owner.kyc_complete ? t("owner.identity.complete") : t("owner.identity.incomplete")}
        </p>
        <div className="customer-photos__grid">
          <LiveCapturePhotoField
            label={t("owner.identity.profilePhoto")}
            value={owner.avatar_url ?? ""}
            onChange={() => undefined}
            allowClear={false}
            facingMode="user"
            hint={t("owner.identity.profilePhotoHint")}
            upload={async (blob) => {
              const next = await uploadOwnerAvatar(blob);
              await apply(next);
              return next.avatar_url ?? "";
            }}
          />
          <LiveCapturePhotoField
            label={t("owner.identity.livePhoto")}
            value={owner.live_photo_url ?? ""}
            onChange={() => undefined}
            allowClear={false}
            requireLiveCapture
            facingMode="user"
            hint={t("owner.identity.livePhotoHint")}
            upload={async (blob, isLive) => {
              if (!isLive) throw new Error(t("owner.identity.liveRequired"));
              const next = await uploadOwnerLivePhoto(blob);
              await apply(next);
              return next.live_photo_url ?? "";
            }}
          />
        </div>
        <form className="owner-form owner-form--wide" onSubmit={saveIds}>
          <div className="form-row">
            <label>
              {t("owner.identity.aadhaar")}
              <input
                value={aadhaar}
                onChange={(e) => setAadhaar(e.target.value.replace(/\D/g, "").slice(0, 12))}
                inputMode="numeric"
                autoComplete="off"
                placeholder={owner.aadhaar_masked ?? "2341 2341 2347"}
              />
            </label>
            <label>
              {t("owner.identity.pan")}
              <input
                value={pan}
                onChange={(e) => setPan(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10))}
                autoComplete="off"
                placeholder={owner.pan_masked ?? "ABCDE1234F"}
              />
            </label>
          </div>
          <p className="auth-card__hint">{t("owner.identity.idsHint")}</p>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? t("owner.identity.saving") : t("owner.identity.saveIds")}
          </button>
        </form>
      </div>
    </OwnerPanel>
  );
}
