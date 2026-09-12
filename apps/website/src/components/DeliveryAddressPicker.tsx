import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { isCustomerSignedIn, useCustomerAuth } from "../shared/customerAuth";
import { useCustomerDelivery } from "../shared/customerDelivery";
import { formatAddressChoice, formatAddressLine } from "../shared/customerDeliveryLocation";

type Variant = "hero" | "bar" | "nav" | "checkout";

export function DeliveryAddressPicker({ variant = "bar" }: { variant?: Variant }) {
  const { t } = useTranslation();
  const { session } = useCustomerAuth();
  const {
    addresses,
    selectedAddress,
    selectedAddressId,
    source,
    selectAddress,
    useGps,
    useDemo,
    geoStatus,
    hint,
  } = useCustomerDelivery();

  const signedIn = isCustomerSignedIn(session);
  const selectValue =
    source === "demo" ? "__demo__" : source === "gps" || !selectedAddressId ? "__gps__" : selectedAddressId;

  const onChange = (value: string) => {
    if (value === "__gps__") {
      useGps();
      return;
    }
    if (value === "__demo__") {
      useDemo();
      return;
    }
    selectAddress(value);
  };

  return (
    <div className={`deliver-picker deliver-picker--${variant}`}>
      <label className="deliver-picker__field">
        <span className="deliver-picker__label">{t("customer.delivery.deliverTo")}</span>
        <select
          value={selectValue}
          onChange={(e) => onChange(e.target.value)}
          aria-label={t("customer.delivery.deliverTo")}
          disabled={geoStatus === "loading" && source === "gps"}
        >
          {addresses.map((address) => (
            <option key={address.id} value={address.id}>
              {formatAddressChoice(address)}
            </option>
          ))}
          <option value="__gps__">
            {geoStatus === "loading" ? t("common.loading") : t("customer.delivery.useGps")}
          </option>
          <option value="__demo__">{t("customer.delivery.demoPune")}</option>
        </select>
      </label>
      {variant !== "nav" && selectedAddress ? (
        <p className="deliver-picker__hint">{formatAddressLine(selectedAddress)}</p>
      ) : null}
      {variant !== "nav" && hint ? <p className="deliver-picker__hint">{hint}</p> : null}
      {variant !== "nav" ? (
        <div className="deliver-picker__actions">
          {signedIn ? (
            <>
              {selectedAddress ? (
                <Link
                  to={`/dashboard?tab=addresses&edit=${selectedAddress.id}`}
                  className="btn btn--ghost btn--sm"
                >
                  {t("customer.delivery.editThisAddress")}
                </Link>
              ) : null}
              <Link to="/dashboard?tab=addresses" className="btn btn--ghost btn--sm">
                {addresses.length ? t("customer.delivery.manage") : t("customer.delivery.addAddress")}
              </Link>
            </>
          ) : (
            <Link to="/login?next=/" className="btn btn--ghost btn--sm">
              {t("customer.delivery.signInToSave")}
            </Link>
          )}
        </div>
      ) : null}
    </div>
  );
}
