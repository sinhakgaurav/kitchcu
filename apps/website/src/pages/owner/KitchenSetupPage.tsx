import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createKitchen } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function KitchenSetupPage() {
  const navigate = useNavigate();
  const { reloadKitchens, kitchen } = useKitchen();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setError("");
    setBusy(true);
    try {
      await createKitchen({
        name: String(fd.get("name")),
        address_line: String(fd.get("address")),
        city: String(fd.get("city")),
        state: String(fd.get("state")),
        latitude: Number(fd.get("latitude") || 18.5362),
        longitude: Number(fd.get("longitude") || 73.8958),
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
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>{kitchen ? "Kitchen settings" : "Create your kitchen"}</h1>
          <p>{kitchen ? "Your kitchen is active on kitchCU." : "Set up your cloud kitchen to start taking orders."}</p>
        </div>
      </header>

      {kitchen ? (
        <div className="glass owner-kitchen-info">
          <p><strong>Name:</strong> {kitchen.name}</p>
          <p><strong>Code:</strong> {kitchen.code}</p>
          <p><strong>Location:</strong> {kitchen.city}, {kitchen.state}</p>
          <p><strong>Delivery radius:</strong> {kitchen.free_delivery_radius_km}–{kitchen.max_delivery_radius_km} km</p>
        </div>
      ) : (
        <form className="glass owner-form" onSubmit={handleSubmit}>
          {error && <div className="auth-card__error">{error}</div>}
          <label>Kitchen name<input name="name" required placeholder="Raj Home Kitchen" /></label>
          <label>Address<input name="address" required placeholder="Koregaon Park" /></label>
          <div className="form-row">
            <label>City<input name="city" required placeholder="Pune" defaultValue="Pune" /></label>
            <label>State<input name="state" required placeholder="Maharashtra" defaultValue="Maharashtra" /></label>
          </div>
          <label>Pincode<input name="pincode" placeholder="411001" /></label>
          <div className="form-row">
            <label>Latitude<input name="latitude" type="number" step="any" defaultValue="18.5362" /></label>
            <label>Longitude<input name="longitude" type="number" step="any" defaultValue="73.8958" /></label>
          </div>
          <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
            {busy ? "Creating..." : "Create Kitchen"}
          </button>
        </form>
      )}
    </div>
  );
}
