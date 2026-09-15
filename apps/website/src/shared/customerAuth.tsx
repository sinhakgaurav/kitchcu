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
  clearCustomerToken,
  fetchCustomerProfile,
  getCustomerToken,
  setCustomerToken,
  type CustomerAuthResult,
} from "./customerApi";
import {
  clearCustomerSession,
  getCustomerSession,
  setCustomerSession,
  type CustomerSession,
} from "./customerSession";
import { clearStoredDeliverySelection } from "./customerDeliveryLocation";

type CustomerAuthState = {
  session: CustomerSession | null;
  loading: boolean;
  login: (name: string, phone: string) => void;
  applyAuthResult: (result: CustomerAuthResult) => void;
  logout: () => void;
  updateSession: (session: CustomerSession) => void;
};

const CustomerAuthContext = createContext<CustomerAuthState | null>(null);

export function CustomerAuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<CustomerSession | null>(() => getCustomerSession());
  const [loading, setLoading] = useState(true);

  const applyAuthResult = useCallback((result: CustomerAuthResult) => {
    setCustomerToken(result.access_token);
    const next: CustomerSession = {
      customerId: result.customer.id,
      name: result.customer.name,
      phone: result.customer.phone ?? "",
      email: result.customer.email,
      avatarUrl: result.customer.avatar_url,
      livePhotoUrl: result.customer.live_photo_url,
      authProvider: session?.authProvider ?? "oauth",
      savedKitchens: session?.savedKitchens ?? [],
    };
    setCustomerSession(next);
    setSessionState(next);
  }, [session?.authProvider, session?.savedKitchens]);

  const login = useCallback((name: string, phone: string) => {
    const next: CustomerSession = {
      name: name.trim(),
      phone: phone.trim(),
      savedKitchens: session?.savedKitchens ?? [],
    };
    setCustomerSession(next);
    setSessionState(next);
  }, [session?.savedKitchens]);

  const logout = useCallback(() => {
    clearCustomerSession();
    clearCustomerToken();
    clearStoredDeliverySelection();
    setSessionState(null);
  }, []);

  const updateSession = useCallback((next: CustomerSession) => {
    setCustomerSession(next);
    setSessionState(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const token = getCustomerToken();
    if (!token) {
      setLoading(false);
      return;
    }

    fetchCustomerProfile()
      .then((profile) => {
        if (cancelled) return;
        const next: CustomerSession = {
          customerId: profile.id,
          name: profile.name,
          phone: profile.phone ?? "",
          email: profile.email,
          avatarUrl: profile.avatar_url,
          livePhotoUrl: profile.live_photo_url,
          savedKitchens: session?.savedKitchens ?? getCustomerSession()?.savedKitchens ?? [],
        };
        setCustomerSession(next);
        setSessionState(next);
      })
      .catch((err) => {
        if (cancelled) return;
        // Only a dead JWT logs the diner out. A gateway blip must not dump them on /login.
        const detail = err instanceof Error ? err.message : "";
        if (isCustomerAuthFailure(detail)) {
          clearCustomerToken();
          clearCustomerSession();
          setSessionState(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({ session, loading, login, applyAuthResult, logout, updateSession }),
    [session, loading, login, applyAuthResult, logout, updateSession],
  );

  return <CustomerAuthContext.Provider value={value}>{children}</CustomerAuthContext.Provider>;
}

export function useCustomerAuth() {
  const ctx = useContext(CustomerAuthContext);
  if (!ctx) throw new Error("useCustomerAuth must be used within CustomerAuthProvider");
  return ctx;
}

export function isCustomerAuthFailure(detail: string): boolean {
  return /invalid token|not authenticated|invalid token type|expired/i.test(detail);
}

export function isCustomerSignedIn(_session?: CustomerSession | null): boolean {
  // JWT is the source of truth. A name/phone stash without a token is not signed in
  // (that used to loop checkout → /login → checkout).
  return Boolean(getCustomerToken());
}

export function customerAccountLabel(session: CustomerSession | null, fallback: string): string {
  const raw = (session?.name || "").trim();
  if (!raw) return fallback;
  const first = raw.split(/\s+/)[0] || raw;
  return first.length > 14 ? `${first.slice(0, 12)}…` : first;
}
