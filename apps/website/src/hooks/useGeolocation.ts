import { useEffect, useState } from "react";

type Coords = { latitude: number; longitude: number };

type Status = "idle" | "loading" | "granted" | "denied";

export function useGeolocation(fallback: Coords) {
  const [coords, setCoords] = useState<Coords>(fallback);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    if (!navigator.geolocation) {
      setStatus("denied");
      setError("Geolocation not supported");
      setCoords(fallback);
      return;
    }
    setStatus("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        });
        setStatus("granted");
        setError(null);
      },
      () => {
        setCoords(fallback);
        setStatus("denied");
        setError("Using default location — enable GPS for accurate results");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  };

  useEffect(() => {
    refresh();
  }, []);

  return { coords, status, error, refresh, setCoords };
}
