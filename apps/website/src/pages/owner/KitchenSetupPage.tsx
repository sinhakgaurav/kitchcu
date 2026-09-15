import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { KitchenLocationMap } from "../../components/owner/KitchenLocationMap";
import { OwnerIdentityPanel } from "../../components/owner/OwnerIdentityPanel";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { useGeolocation } from "../../hooks/useGeolocation";
import { createKitchen, updateKitchenDeliverySettings, updateKitchenProfile } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { customerUrl } from "../../shared/urls";
import { firstError, pincodeInputValue, validatePincode, validateText } from "../../shared/validation";

const PUNE_DEFAULT = { latitude: 18.5362, longitude: 73.8958 };

export function KitchenSetupPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { reloadKitchens, kitchen } = useKitchen();
  const { coords, status: geoStatus, error: geoError, refresh: refreshGeo } = useGeolocation(PUNE_DEFAULT);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    address?: string;
    city?: string;
    state?: string;
    pincode?: string;
  }>({});
  const [draftLat, setDraftLat] = useState(String(PUNE_DEFAULT.latitude));
  const [draftLng, setDraftLng] = useState(String(PUNE_DEFAULT.longitude));
  const [locateRequested, setLocateRequested] = useState(false);

  useEffect(() => {
    if (kitchen?.latitude == null || kitchen?.longitude == null) return;
    setDraftLat(Number(kitchen.latitude).toFixed(6));
    setDraftLng(Number(kitchen.longitude).toFixed(6));
  }, [kitchen?.id]);

  useEffect(() => {
    if (kitchen) return;
    setDraftLat(coords.latitude.toFixed(6));
    setDraftLng(coords.longitude.toFixed(6));
  }, [kitchen, coords.latitude, coords.longitude]);

  useEffect(() => {
    if (!kitchen || !locateRequested || geoStatus === "loading") return;
    setDraftLat(coords.latitude.toFixed(6));
    setDraftLng(coords.longitude.toFixed(6));
    setLocateRequested(false);
  }, [kitchen, locateRequested, geoStatus, coords.latitude, coords.longitude]);

  useEffect(() => {
    if (location.hash !== "#identity") return;
    document.getElementById("identity")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  const draftLatitude = Number(draftLat);
  const draftLongitude = Number(draftLng);
  const draftCoordsValid =
    Number.isFinite(draftLatitude) &&
    Number.isFinite(draftLongitude) &&
    Math.abs(draftLatitude) <= 90 &&
    Math.abs(draftLongitude) <= 180;

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const nextErrors = {
      name: validateText(String(fd.get("name") || ""), "a kitchen name", { min: 2, max: 120 }) ?? undefined,
      address: validateText(String(fd.get("address") || ""), "a street address", { min: 5, max: 200 }) ?? undefined,
      city: validateText(String(fd.get("city") || ""), "a city", { min: 2, max: 80 }) ?? undefined,
      state: validateText(String(fd.get("state") || ""), "a state", { min: 2, max: 80 }) ?? undefined,
      pincode: validatePincode(String(fd.get("pincode") || ""), { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    if (!draftCoordsValid) {
      setError("Enter valid latitude and longitude.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      await createKitchen({
        name: String(fd.get("name")),
        address_line: String(fd.get("address")),
        city: String(fd.get("city")),
        state: String(fd.get("state")),
        latitude: draftLatitude,
        longitude: draftLongitude,
        pincode: String(fd.get("pincode") || "") || undefined,
      });
      await reloadKitchens();
      navigate("/dashboard/menu/new");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create kitchen");
    } finally {
      setBusy(false);
    }
  };

  const handleProfileSave = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!kitchen) return;
    const fd = new FormData(e.currentTarget);
    const nextErrors = {
      name: validateText(String(fd.get("name") || ""), "a kitchen name", { min: 2, max: 120 }) ?? undefined,
      address: validateText(String(fd.get("address") || ""), "a street address", { min: 5, max: 200 }) ?? undefined,
      city: validateText(String(fd.get("city") || ""), "a city", { min: 2, max: 80 }) ?? undefined,
      state: validateText(String(fd.get("state") || ""), "a state", { min: 2, max: 80 }) ?? undefined,
      pincode: validatePincode(String(fd.get("pincode") || ""), { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    if (!draftCoordsValid) {
      setError("Enter valid latitude and longitude.");
      return;
    }
    setError("");
    setSaveMsg("");
    setBusy(true);
    try {
      await updateKitchenProfile(kitchen.id, {
        name: String(fd.get("name")),
        address_line: String(fd.get("address")),
        city: String(fd.get("city")),
        state: String(fd.get("state")),
        pincode: String(fd.get("pincode") || "") || null,
        latitude: draftLatitude,
        longitude: draftLongitude,
      });
      await reloadKitchens();
      setSaveMsg("Kitchen profile and map pin saved. Discovery will use this location.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save kitchen profile");
    } finally {
      setBusy(false);
    }
  };

  const handleDeliverySettings = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!kitchen) return;
    const fd = new FormData(e.currentTarget);
    setError("");
    setSaveMsg("");
    setBusy(true);
    try {
      const minRaw = String(fd.get("min_order_for_free_delivery") || "").trim();
      await updateKitchenDeliverySettings(kitchen.id, {
        free_delivery_radius_km: Number(fd.get("free_delivery_radius_km")),
        max_delivery_radius_km: Number(fd.get("max_delivery_radius_km")),
        delivery_fee_per_km: Number(fd.get("delivery_fee_per_km")),
        delivery_fee_flat_beyond: Number(fd.get("delivery_fee_flat_beyond")),
        min_order_for_free_delivery: minRaw === "" ? null : Number(minRaw),
        delivery_subsidy_percent: Number(fd.get("delivery_subsidy_percent")),
        porter_auto_book_enabled: fd.get("porter_auto_book_enabled") === "on",
        porter_auto_book_delay_min: Number(fd.get("porter_auto_book_delay_min") || 15),
      });
      await reloadKitchens();
      setSaveMsg("Delivery rules saved — cost share + Porter auto-book settings applied.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save delivery settings");
    } finally {
      setBusy(false);
    }
  };

  return (
    <OwnerPageShell
      eyebrow="Settings"
      title={kitchen ? "Kitchen settings" : "Create your kitchen"}
      description={
        kitchen
          ? "Your identity, kitchen profile, delivery radius, and who pays when customers are beyond range"
          : "Identify yourself, then set up your cloud kitchen to start taking orders"
      }
    >
      <OwnerIdentityPanel />
      {kitchen ? (
        <>
          <OwnerPanel
            title="Kitchen profile"
            description={`Code ${kitchen.code} is permanent. City can change without renaming the code.`}
          >
            <form className="owner-form owner-form--wide" onSubmit={handleProfileSave}>
              {error && <div className="auth-card__error">{error}</div>}
              {saveMsg && <p className="owner-muted">{saveMsg}</p>}
              <label>
                Kitchen name
                <input
                  name="name"
                  required
                  defaultValue={kitchen.name}
                  key={`${kitchen.id}-name`}
                  aria-invalid={Boolean(fieldErrors.name)}
                  className={fieldErrors.name ? "input-invalid" : undefined}
                />
                {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
              </label>
              <label>
                Street address
                <input
                  name="address"
                  required
                  defaultValue={kitchen.address_line ?? ""}
                  key={`${kitchen.id}-address`}
                  aria-invalid={Boolean(fieldErrors.address)}
                  className={fieldErrors.address ? "input-invalid" : undefined}
                />
                {fieldErrors.address ? <span className="field-error">{fieldErrors.address}</span> : null}
              </label>
              <div className="form-row">
                <label>
                  City
                  <input
                    name="city"
                    required
                    defaultValue={kitchen.city ?? ""}
                    key={`${kitchen.id}-city`}
                    aria-invalid={Boolean(fieldErrors.city)}
                    className={fieldErrors.city ? "input-invalid" : undefined}
                  />
                  {fieldErrors.city ? <span className="field-error">{fieldErrors.city}</span> : null}
                </label>
                <label>
                  State
                  <input
                    name="state"
                    required
                    defaultValue={kitchen.state ?? ""}
                    key={`${kitchen.id}-state`}
                    aria-invalid={Boolean(fieldErrors.state)}
                    className={fieldErrors.state ? "input-invalid" : undefined}
                  />
                  {fieldErrors.state ? <span className="field-error">{fieldErrors.state}</span> : null}
                </label>
              </div>
              <label>
                Pincode
                <input
                  name="pincode"
                  defaultValue={kitchen.pincode ?? ""}
                  key={`${kitchen.id}-pincode`}
                  inputMode="numeric"
                  maxLength={6}
                  aria-invalid={Boolean(fieldErrors.pincode)}
                  className={fieldErrors.pincode ? "input-invalid" : undefined}
                  onChange={(e) => {
                    e.target.value = pincodeInputValue(e.target.value);
                    setFieldErrors((f) => ({ ...f, pincode: undefined }));
                  }}
                />
                {fieldErrors.pincode ? <span className="field-error">{fieldErrors.pincode}</span> : null}
              </label>
              <div className="form-row">
                <label>
                  Latitude
                  <input
                    value={draftLat}
                    onChange={(e) => setDraftLat(e.target.value)}
                    inputMode="decimal"
                  />
                </label>
                <label>
                  Longitude
                  <input
                    value={draftLng}
                    onChange={(e) => setDraftLng(e.target.value)}
                    inputMode="decimal"
                  />
                </label>
              </div>
              <div className="owner-kitchen-map__locate">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => {
                    setLocateRequested(true);
                    refreshGeo();
                  }}
                >
                  {geoStatus === "loading" ? "Locating…" : "Use my current location"}
                </button>
                {geoError ? <p className="owner-muted">{geoError}</p> : null}
              </div>
              <KitchenLocationMap
                latitude={draftCoordsValid ? draftLatitude : kitchen.latitude}
                longitude={draftCoordsValid ? draftLongitude : kitchen.longitude}
                name={kitchen.name}
                addressLine={kitchen.address_line}
                city={kitchen.city}
                state={kitchen.state}
                pincode={kitchen.pincode}
              />
              <button type="submit" className="btn btn--primary" disabled={busy}>
                {busy ? "Saving…" : "Save profile and map pin"}
              </button>
            </form>
          </OwnerPanel>

          <OwnerPanel
            title="Brand page"
            description="Share your kitchen-first storefront with customers — publish tagline and /k/code link."
          >
            <p className="owner-muted" style={{ marginBottom: "0.75rem" }}>
              Public link:{" "}
              <code>{customerUrl(`/k/${kitchen.code}`)}</code>
              {kitchen.branded_page?.enabled ? " · Published" : " · Not published yet"}
            </p>
            <Link to="/dashboard/brand" className="btn btn--primary btn--sm">
              Open Brand page
            </Link>
          </OwnerPanel>

          <OwnerPanel
            title="Delivery cost share"
            description="In range: kitchen pays 100%. Beyond max radius: kitchen pays your subsidy % only if cart meets min order; otherwise customer pays full."
          >
            <form className="owner-form owner-form--wide" onSubmit={handleDeliverySettings}>
              {error && <div className="auth-card__error">{error}</div>}
              {saveMsg && <p className="owner-muted">{saveMsg}</p>}
              <div className="form-row">
                <label>
                  Free radius (km)
                  <input
                    name="free_delivery_radius_km"
                    type="number"
                    step="0.1"
                    min={0.1}
                    required
                    defaultValue={kitchen.free_delivery_radius_km}
                  />
                </label>
                <label>
                  Max radius (km)
                  <input
                    name="max_delivery_radius_km"
                    type="number"
                    step="0.1"
                    min={0.1}
                    required
                    defaultValue={kitchen.max_delivery_radius_km}
                  />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Self fee per km (₹)
                  <input
                    name="delivery_fee_per_km"
                    type="number"
                    step="1"
                    min={0}
                    required
                    defaultValue={kitchen.delivery_fee_per_km ?? 10}
                  />
                </label>
                <label>
                  Flat fee beyond free (₹)
                  <input
                    name="delivery_fee_flat_beyond"
                    type="number"
                    step="1"
                    min={0}
                    required
                    defaultValue={kitchen.delivery_fee_flat_beyond ?? 0}
                  />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Min order for kitchen subsidy (₹)
                  <input
                    name="min_order_for_free_delivery"
                    type="number"
                    step="1"
                    min={0}
                    placeholder="e.g. 349 — leave empty for none"
                    defaultValue={kitchen.min_order_for_free_delivery ?? ""}
                  />
                </label>
                <label>
                  Kitchen subsidy beyond range (%)
                  <input
                    name="delivery_subsidy_percent"
                    type="number"
                    step="1"
                    min={0}
                    max={100}
                    required
                    defaultValue={kitchen.delivery_subsidy_percent ?? 50}
                  />
                </label>
              </div>
              <div className="form-row">
                <label className="owner-check">
                  <input
                    name="porter_auto_book_enabled"
                    type="checkbox"
                    defaultChecked={kitchen.porter_auto_book_enabled !== false}
                  />
                  Auto-book Porter after accept (platform delivery)
                </label>
                <label>
                  Auto-book delay (minutes)
                  <input
                    name="porter_auto_book_delay_min"
                    type="number"
                    min={1}
                    max={120}
                    required
                    defaultValue={kitchen.porter_auto_book_delay_min ?? 15}
                  />
                </label>
              </div>
              <p className="owner-muted">
                When enabled, the platform books Porter after the delay so the courier arrives near
                food-ready time, and retries every few minutes until booked. Off = book immediately on accept.
              </p>
              <button type="submit" className="btn btn--primary" disabled={busy}>
                {busy ? "Saving…" : "Save delivery rules"}
              </button>
            </form>
          </OwnerPanel>

        </>
      ) : (
        <form className="dash-card owner-form owner-form--wide" onSubmit={handleSubmit}>
          {error && <div className="auth-card__error">{error}</div>}
          <label>
            Kitchen name
            <input
              name="name"
              required
              placeholder="Raj Home Kitchen"
              aria-invalid={Boolean(fieldErrors.name)}
              className={fieldErrors.name ? "input-invalid" : undefined}
            />
            {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
          </label>
          <label>
            Street address
            <input
              name="address"
              required
              placeholder="Koregaon Park, Lane 5"
              aria-invalid={Boolean(fieldErrors.address)}
              className={fieldErrors.address ? "input-invalid" : undefined}
            />
            {fieldErrors.address ? <span className="field-error">{fieldErrors.address}</span> : null}
          </label>
          <div className="form-row">
            <label>
              City
              <input
                name="city"
                required
                placeholder="Pune"
                defaultValue="Pune"
                aria-invalid={Boolean(fieldErrors.city)}
                className={fieldErrors.city ? "input-invalid" : undefined}
              />
              {fieldErrors.city ? <span className="field-error">{fieldErrors.city}</span> : null}
            </label>
            <label>
              State
              <input
                name="state"
                required
                placeholder="Maharashtra"
                defaultValue="Maharashtra"
                aria-invalid={Boolean(fieldErrors.state)}
                className={fieldErrors.state ? "input-invalid" : undefined}
              />
              {fieldErrors.state ? <span className="field-error">{fieldErrors.state}</span> : null}
            </label>
          </div>
          <label>
            Pincode
            <input
              name="pincode"
              placeholder="411001"
              inputMode="numeric"
              maxLength={6}
              aria-invalid={Boolean(fieldErrors.pincode)}
              className={fieldErrors.pincode ? "input-invalid" : undefined}
              onChange={(e) => {
                e.target.value = pincodeInputValue(e.target.value);
                setFieldErrors((f) => ({ ...f, pincode: undefined }));
              }}
            />
            {fieldErrors.pincode ? <span className="field-error">{fieldErrors.pincode}</span> : null}
          </label>

          <div className="owner-kitchen-map__locate">
            <div>
              <strong>Map pin</strong>
              <p className="owner-muted">Use your phone GPS or enter coordinates manually.</p>
              {geoError && <p className="form-error">{geoError}</p>}
            </div>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={refreshGeo}
              disabled={geoStatus === "loading"}
            >
              {geoStatus === "loading" ? "Locating…" : "Use my location"}
            </button>
          </div>

          <div className="form-row">
            <label>
              Latitude
              <input
                name="latitude"
                type="number"
                step="any"
                required
                value={draftLat}
                onChange={(e) => setDraftLat(e.target.value)}
              />
            </label>
            <label>
              Longitude
              <input
                name="longitude"
                type="number"
                step="any"
                required
                value={draftLng}
                onChange={(e) => setDraftLng(e.target.value)}
              />
            </label>
          </div>

          {draftCoordsValid && (
            <KitchenLocationMap
              latitude={draftLatitude}
              longitude={draftLongitude}
              name={undefined}
            />
          )}

          <button type="submit" className="btn btn--primary btn--lg" disabled={busy || !draftCoordsValid}>
            {busy ? "Creating..." : "Create Kitchen"}
          </button>
        </form>
      )}
    </OwnerPageShell>
  );
}
