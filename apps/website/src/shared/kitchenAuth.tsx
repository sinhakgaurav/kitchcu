import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearToken,
  fetchKitchens,
  fetchOwnerProfile,
  getToken,
  setToken,
  type Kitchen,
  type OwnerProfile,
} from "./api";

type AuthState = {
  token: string | null;
  owner: OwnerProfile | null;
  kitchens: Kitchen[];
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function KitchenAuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [owner, setOwner] = useState<OwnerProfile | null>(null);
  const [kitchens, setKitchens] = useState<Kitchen[]>([]);
  const [loading, setLoading] = useState(!!getToken());

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setOwner(null);
      setKitchens([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [profile, kitchenList] = await Promise.all([fetchOwnerProfile(), fetchKitchens()]);
      setOwner(profile);
      setKitchens(kitchenList);
    } catch {
      clearToken();
      setTokenState(null);
      setOwner(null);
      setKitchens([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(
    async (newToken: string) => {
      setToken(newToken);
      setTokenState(newToken);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setOwner(null);
    setKitchens([]);
  }, []);

  useEffect(() => {
    if (token) refresh();
    else setLoading(false);
  }, [token, refresh]);

  const value = useMemo(
    () => ({ token, owner, kitchens, loading, login, logout, refresh }),
    [token, owner, kitchens, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useKitchenAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useKitchenAuth must be used within KitchenAuthProvider");
  return ctx;
}
