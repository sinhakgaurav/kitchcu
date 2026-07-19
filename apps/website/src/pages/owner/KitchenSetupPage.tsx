import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { KitchenLocationMap } from "../../components/owner/KitchenLocationMap";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { useGeolocation } from "../../hooks/useGeolocation";
import { formatKitchenAddress } from "../../lib/locationMaps";
import { createKitchen, updateKitchenDeliverySettings } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { customerUrl } from "../../shared/urls";

const PUNE_DEFAULT = { latitude: 18.5362, longitude: 73.8958 };

export function KitchenSetupPage() {
  const navigate = useNavigate();
  const { reloadKitchens, kitchen } = useKitchen();
  const { coords, status: geoStatus, error: geoError, refresh: refreshGeo } = useGeolocation(PUNE_DEFAULT);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [draftLat, setDraftLat] = useState(String(PUNE_DEFAULT.latitude));
  const [draftLng, setDraftLng] = useState(String(PUNE_DEFAULT.longitude));

  useEffect(() => {
    setDraftLat(coords.latitude.toFixed(6));
    setDraftLng(coords.longitude.toFixed(6));
  }, [coords.latitude, coords.longitude]);

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
      navigate("/dashboard/brand");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create kitchen");
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
          ? "Profile, delivery radius, and who pays when customers are beyond range"
          : "Set up your cloud kitchen to start taking orders"
      }
    >
      {kitchen ? (
        <>
          <OwnerPanel title="Kitchen profile">
            <div className="owner-kitchen-info">
              <p><strong>Name:</strong> {kitchen.name}</p>
              <p><strong>Code:</strong> {kitchen.code}</p>
              <p>
                <strong>Address:</strong>{" "}
                {formatKitchenAddress({
                  addressLine: kitchen.address_line,
                  city: kitchen.city,
                  state: kitchen.state,
                  pincode: kitchen.pincode,
                }) || "—"}
              </p>
            </div>
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

          <OwnerPanel
            title="Location on map"
            description="Customers use this pin for nearby discovery and delivery distance"
          >
            <KitchenLocationMap
              latitude={kitchen.latitude}
              longitude={kitchen.longitude}
              name={kitchen.name}
              addressLine={kitchen.address_line}
              city={kitchen.city}
              state={kitchen.state}
              pincode={kitchen.pincode}
            />
          </OwnerPanel>
        </>
      ) : (
        <form className="dash-card owner-form owner-form--wide" onSubmit={handleSubmit}>
          {error && <div className="auth-card__error">{error}</div>}
          <label>Kitchen name<input name="name" required placeholder="Raj Home Kitchen" /></label>
          <label>Street address<input name="address" required placeholder="Koregaon Park, Lane 5" /></label>
          <div className="form-row">
            <label>City<input name="city" required placeholder="Pune" defaultValue="Pune" /></label>
            <label>State<input name="state" required placeholder="Maharashtra" defaultValue="Maharashtra" /></label>
          </div>
          <label>Pincode<input name="pincode" placeholder="411001" /></label>

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
