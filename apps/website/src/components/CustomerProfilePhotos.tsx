import { useTranslation } from "react-i18next";
import { LiveCapturePhotoField } from "./LiveCapturePhotoField";
import {
  uploadCustomerAvatar,
  uploadCustomerLivePhoto,
  type CustomerProfile,
} from "../shared/customerApi";
import { useCustomerAuth } from "../shared/customerAuth";

export function CustomerProfilePhotos({
  profile,
  onUpdated,
}: {
  profile: CustomerProfile;
  onUpdated: (next: CustomerProfile) => void;
}) {
  const { t } = useTranslation();
  const { session, updateSession } = useCustomerAuth();

  const apply = (next: CustomerProfile) => {
    onUpdated(next);
    if (session) {
      updateSession({
        ...session,
        name: next.name,
        email: next.email,
        avatarUrl: next.avatar_url,
        livePhotoUrl: next.live_photo_url,
      });
    }
  };

  return (
    <section className="glass customer-dash__card customer-photos">
      <div className="customer-photos__intro">
        <h2>{t("customer.account.photosTitle")}</h2>
        <p className="auth-card__hint">{t("customer.account.photosHint")}</p>
      </div>
      <div className="customer-photos__grid">
        <LiveCapturePhotoField
          label={t("customer.account.profilePhoto")}
          value={profile.avatar_url ?? ""}
          onChange={() => undefined}
          allowClear={false}
          facingMode="user"
          hint={t("customer.account.profilePhotoHint")}
          upload={async (blob) => {
            const next = await uploadCustomerAvatar(blob);
            apply(next);
            return next.avatar_url ?? "";
          }}
        />
        <LiveCapturePhotoField
          label={t("customer.account.livePhoto")}
          value={profile.live_photo_url ?? ""}
          onChange={() => undefined}
          allowClear={false}
          requireLiveCapture
          facingMode="user"
          hint={t("customer.account.livePhotoHint")}
          upload={async (blob, isLive) => {
            if (!isLive) {
              throw new Error(t("customer.account.livePhotoRequired"));
            }
            const next = await uploadCustomerLivePhoto(blob);
            apply(next);
            return next.live_photo_url ?? "";
          }}
        />
      </div>
    </section>
  );
}
