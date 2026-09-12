import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { DEMO } from "./demo";
import { getCustomerToken } from "./customerApi";
import { useCustomerAuth } from "./customerAuth";
import { fetchMyAddresses, type CustomerAddress } from "./customerDashboardApi";
import {
  clearStoredDeliverySelection,
  pickDeliveryAddress,
  readStoredDeliverySelection,
  resolveAddressCoords,
  writeStoredDeliverySelection,
  type DeliveryCoords,
  type DeliverySource,
} from "./customerDeliveryLocation";

const DEMO_PIN: DeliveryCoords = {
  latitude: DEMO.defaultLocation.latitude,
  longitude: DEMO.defaultLocation.longitude,
};

type GeoStatus = "idle" | "loading" | "granted" | "denied";

type CustomerDeliveryState = {
  addresses: CustomerAddress[];
  selectedAddress: CustomerAddress | null;
  selectedAddressId: string;
  source: DeliverySource;
  coords: DeliveryCoords;
  loading: boolean;
  geoStatus: GeoStatus;
  geoError: string | null;
  hint: string | null;
  selectAddress: (addressId: string) => void;
  useGps: () => void;
  useDemo: () => void;
  refreshAddresses: () => Promise<CustomerAddress[]>;
};

const CustomerDeliveryContext = createContext<CustomerDeliveryState | null>(null);

function readGps(fallback: DeliveryCoords): Promise<{ coords: DeliveryCoords; granted: boolean; error: string | null }> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve({
      coords: fallback,
      granted: false,
      error: "Geolocation not supported — using a default pin",
    });
  }
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => {
      resolve({
        coords: fallback,
        granted: false,
        error: "Location timed out — using default. Enable GPS or pick a saved address.",
      });
    }, 12000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        window.clearTimeout(timer);
        resolve({
          coords: { latitude: pos.coords.latitude, longitude: pos.coords.longitude },
          granted: true,
          error: null,
        });
      },
      () => {
        window.clearTimeout(timer);
        resolve({
          coords: fallback,
          granted: false,
          error: "Using default location — enable GPS or pick a saved address",
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  });
}

export function CustomerDeliveryProvider({ children }: { children: ReactNode }) {
  const { session, loading: authLoading } = useCustomerAuth();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [source, setSource] = useState<DeliverySource>("gps");
  const [coords, setCoords] = useState<DeliveryCoords>(DEMO_PIN);
  const [loading, setLoading] = useState(true);
  const [geoStatus, setGeoStatus] = useState<GeoStatus>("idle");
  const [geoError, setGeoError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const gpsGeneration = useRef(0);
  const addressesRef = useRef<CustomerAddress[]>([]);

  const customerId = session?.customerId ?? null;

  const persist = useCallback(
    (nextSource: DeliverySource, addressId: string) => {
      if (!customerId || nextSource !== "address" || !addressId) {
        if (!customerId) clearStoredDeliverySelection();
        return;
      }
      writeStoredDeliverySelection({ customerId, addressId, source: nextSource });
    },
    [customerId],
  );

  const applyAddress = useCallback(
    (address: CustomerAddress) => {
      const pin = resolveAddressCoords(address);
      setSelectedAddressId(address.id);
      persist("address", address.id);
      if (pin) {
        setSource("address");
        setCoords(pin);
        setHint(null);
        setGeoError(null);
        setGeoStatus("granted");
        return true;
      }
      setHint("This address has no map pin — using GPS for kitchen distance.");
      return false;
    },
    [persist],
  );

  const startGps = useCallback(async () => {
    const gen = ++gpsGeneration.current;
    setSource("gps");
    setGeoStatus("loading");
    setHint(null);
    const result = await readGps(DEMO_PIN);
    if (gen !== gpsGeneration.current) return;
    setCoords(result.coords);
    setGeoStatus(result.granted ? "granted" : "denied");
    setGeoError(result.error);
  }, []);

  const refreshAddresses = useCallback(async () => {
      if (!getCustomerToken()) {
      addressesRef.current = [];
      setAddresses([]);
      return [];
    }
    try {
      const list = await fetchMyAddresses();
      addressesRef.current = list;
      setAddresses(list);
      return list;
      } catch {
      addressesRef.current = [];
      setAddresses([]);
      return [];
    }
  }, []);

  const selectAddress = useCallback(
    (addressId: string) => {
      gpsGeneration.current += 1;
      const address = addressesRef.current.find((row) => row.id === addressId);
      if (!address) return;
      if (!applyAddress(address)) {
        void startGps();
      }
    },
    [applyAddress, startGps],
  );

  const useGps = useCallback(() => {
    gpsGeneration.current += 1;
    setSelectedAddressId("");
    persist("gps", "");
    void startGps();
  }, [persist, startGps]);

  const useDemo = useCallback(() => {
    gpsGeneration.current += 1;
    setSelectedAddressId("");
    setSource("demo");
    setCoords(DEMO_PIN);
    setGeoStatus("granted");
    setGeoError(null);
    setHint(`Showing demo kitchens near ${DEMO.defaultLocation.label}.`);
    persist("demo", "");
  }, [persist]);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      if (authLoading) return;
      setLoading(true);
      const signedIn = Boolean(getCustomerToken() && customerId);
      if (!signedIn) {
        clearStoredDeliverySelection();
        setAddresses([]);
        setSelectedAddressId("");
        if (!cancelled) {
          await startGps();
          setLoading(false);
        }
        return;
      }
      const list = await refreshAddresses();
      if (cancelled) return;
      const stored = readStoredDeliverySelection(customerId);
      const picked = pickDeliveryAddress(list, stored?.addressId);
      if (picked && applyAddress(picked)) {
        setLoading(false);
        return;
      }
      if (stored?.source === "demo") {
        gpsGeneration.current += 1;
        setSelectedAddressId("");
        setSource("demo");
        setCoords(DEMO_PIN);
        setGeoStatus("granted");
        setGeoError(null);
        setHint(`Showing demo kitchens near ${DEMO.defaultLocation.label}.`);
        setLoading(false);
        return;
      }
      await startGps();
      setLoading(false);
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, [authLoading, customerId, applyAddress, refreshAddresses, startGps]);

  const selectedAddress = useMemo(
    () => addresses.find((row) => row.id === selectedAddressId) ?? null,
    [addresses, selectedAddressId],
  );

  const value = useMemo<CustomerDeliveryState>(
    () => ({
      addresses,
      selectedAddress,
      selectedAddressId,
      source,
      coords,
      loading,
      geoStatus,
      geoError,
      hint,
      selectAddress,
      useGps,
      useDemo,
      refreshAddresses,
    }),
    [
      addresses,
      selectedAddress,
      selectedAddressId,
      source,
      coords,
      loading,
      geoStatus,
      geoError,
      hint,
      selectAddress,
      useGps,
      useDemo,
      refreshAddresses,
    ],
  );

  return <CustomerDeliveryContext.Provider value={value}>{children}</CustomerDeliveryContext.Provider>;
}

export function useCustomerDelivery(): CustomerDeliveryState {
  const ctx = useContext(CustomerDeliveryContext);
  if (!ctx) throw new Error("useCustomerDelivery must be used within CustomerDeliveryProvider");
  return ctx;
}

export function useOptionalCustomerDelivery(): CustomerDeliveryState | null {
  return useContext(CustomerDeliveryContext);
}
