import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { KitchenLocationMap } from "../../components/owner/KitchenLocationMap";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { useGeolocation } from "../../hooks/useGeolocation";
import { formatKitchenAddress } from "../../lib/locationMaps";
import { createKitchen } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const PUNE_DEFAULT = { latitude: 18.5362, longitude: 73.8958 };

export function KitchenSetupPage() {
  const navigate = useNavigate();
  const { reloadKitchens, kitchen } = useKitchen();
  const { coords, status: geoStatus, error: geoError, refresh: refreshGeo } = useGeolocation(PUNE_DEFAULT);
  const [error, setError] = useState("");
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
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create kitchen");
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
          ? "Profile, delivery radius, and map pin for customer discovery"
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
              <p>
                <strong>Delivery radius:</strong> {kitchen.free_delivery_radius_km}–{kitchen.max_delivery_radius_km} km
              </p>
            </div>
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
