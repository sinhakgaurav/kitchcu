import { useCallback, useEffect, useRef, useState } from "react";

type Coords = { latitude: number; longitude: number };

type Status = "idle" | "loading" | "granted" | "denied";

const WATCHDOG_MS = 15000;

export function useGeolocation(fallback: Coords) {
  const [coords, setCoords] = useState<Coords>(fallback);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const watchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallbackRef = useRef(fallback);
  fallbackRef.current = fallback;

  const clearWatchdog = () => {
    if (watchdogRef.current) {
      clearTimeout(watchdogRef.current);
      watchdogRef.current = null;
    }
  };

  const refresh = useCallback(() => {
    const pin = fallbackRef.current;
    clearWatchdog();
    if (!navigator.geolocation) {
      setStatus("denied");
      setError("Geolocation not supported");
      setCoords(pin);
      return;
    }
    setStatus("loading");
    watchdogRef.current = setTimeout(() => {
      setCoords(pin);
      setStatus("denied");
      setError("Location timed out — using default. Enable GPS or show demo kitchens.");
      watchdogRef.current = null;
    }, WATCHDOG_MS);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearWatchdog();
        setCoords({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        });
        setStatus("granted");
        setError(null);
      },
      () => {
        clearWatchdog();
        setCoords(pin);
        setStatus("denied");
        setError("Using default location — enable GPS for accurate results");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  }, []);

  useEffect(() => {
    refresh();
    return clearWatchdog;
  }, [refresh]);

  return { coords, status, error, refresh, setCoords };
}
