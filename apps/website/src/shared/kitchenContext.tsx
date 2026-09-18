import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fetchKitchens, getStoredKitchenId, setStoredKitchenId, type Kitchen } from "./api";
import { useKitchenAuth } from "./kitchenAuth";

type KitchenState = {
  kitchens: Kitchen[];
  kitchen: Kitchen | null;
  setKitchenId: (id: string) => void;
  reloadKitchens: () => Promise<void>;
  loading: boolean;
  loadError: string | null;
};

const KitchenContext = createContext<KitchenState | null>(null);

export function KitchenProvider({ children }: { children: ReactNode }) {
  const { token } = useKitchenAuth();
  const [kitchens, setKitchens] = useState<Kitchen[]>([]);
  const [kitchenId, setKitchenIdState] = useState<string | null>(() => getStoredKitchenId());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const reloadKitchens = useCallback(async () => {
    if (!token) {
      setKitchens([]);
      setLoadError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const raw = await fetchKitchens();
      const list = (Array.isArray(raw) ? raw : [])
        .slice()
        .sort((a, b) => String(a.code || "").localeCompare(String(b.code || "")));
      setKitchens(list);
      setLoadError(null);
      const stored = getStoredKitchenId();
      const valid = list.find((k) => k.id === stored);
      if (valid) {
        setKitchenIdState(valid.id);
      } else if (list.length > 0) {
        setKitchenIdState(list[0].id);
        setStoredKitchenId(list[0].id);
      } else {
        setKitchenIdState(null);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Could not load kitchens");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    reloadKitchens();
  }, [reloadKitchens]);

  const setKitchenId = useCallback((id: string) => {
    setKitchenIdState(id);
    setStoredKitchenId(id);
  }, []);

  const kitchen = kitchens.find((k) => k.id === kitchenId) ?? null;

  const value = useMemo(
    () => ({ kitchens, kitchen, setKitchenId, reloadKitchens, loading, loadError }),
    [kitchens, kitchen, setKitchenId, reloadKitchens, loading, loadError],
  );

  return <KitchenContext.Provider value={value}>{children}</KitchenContext.Provider>;
}

export function useKitchen() {
  const ctx = useContext(KitchenContext);
  if (!ctx) throw new Error("useKitchen must be used within KitchenProvider");
  return ctx;
}
