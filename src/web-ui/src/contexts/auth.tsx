"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";
import { api, User } from "@/lib/api";
import { AuthExpiredError } from "@/lib/api/base";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, kennitala: string) => Promise<User>;
  logout: () => Promise<void>;
  getToken: () => string | null;
  refreshUser: () => Promise<User | null>;
  verifyEmail: (code: string) => Promise<boolean>;
  resendVerification: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Waits between attempts when the startup check fails for a reason that says
// nothing about the session (network error, 5xx, 429). Twelve seconds covers a
// pod rollover and a cold connection; past that, a placeholder that never
// resolves is worse than a wrong button.
const STARTUP_RETRY_DELAYS_MS = [1000, 3000, 8000];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Set when the startup check gave up without an answer. Until someone gets
  // one, the events below run the check again.
  const awaitingRecovery = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let checking = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const wait = (ms: number) =>
      new Promise<void>((resolve) => {
        retryTimer = setTimeout(resolve, ms);
      });

    // "settled" means the question is answered either way: the user is loaded,
    // or the backend rejected the refresh token and the session is over.
    const loadUser = async (): Promise<"settled" | "transient"> => {
      try {
        if (!api.isAuthenticated()) {
          await api.auth.restoreSession();
        }
        const userData = await api.auth.getCurrentUser();
        if (!cancelled) {
          setUser(userData);
        }
        return "settled";
      } catch (err) {
        // APIClient owns the clear-tokens decision (see base.ts): it clears on
        // a real auth failure and dispatches "auth:logout", but keeps tokens
        // on transient errors (5xx, network) so the user stays logged in once
        // connectivity recovers. Don't second-guess it here.
        return err instanceof AuthExpiredError ? "settled" : "transient";
      }
    };

    // isLoading stays true through the retries, so the header shows its
    // placeholder rather than "Log in" while the credentials are still good.
    const checkAuth = async (retryDelays: number[]) => {
      if (checking) return;
      checking = true;
      awaitingRecovery.current = false;

      let outcome = await loadUser();
      for (const delay of retryDelays) {
        if (cancelled || outcome === "settled") break;
        await wait(delay);
        if (cancelled) break;
        outcome = await loadUser();
      }

      checking = false;
      if (cancelled) return;
      awaitingRecovery.current = outcome === "transient";
      setIsLoading(false);
    };

    checkAuth(STARTUP_RETRY_DELAYS_MS);

    const recheck = () => {
      if (awaitingRecovery.current) {
        checkAuth([]);
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        recheck();
      }
    };

    // Listen for logout events (e.g., 401 responses)
    const handleLogout = () => {
      awaitingRecovery.current = false;
      setUser(null);
    };

    window.addEventListener("auth:logout", handleLogout);
    window.addEventListener("auth:refreshed", recheck);
    window.addEventListener("online", recheck);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      window.removeEventListener("auth:logout", handleLogout);
      window.removeEventListener("auth:refreshed", recheck);
      window.removeEventListener("online", recheck);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    await api.auth.login(email, password);
    const userData = await api.auth.getCurrentUser();
    awaitingRecovery.current = false;
    setUser(userData);
    return userData;
  };

  const register = async (email: string, password: string, kennitala: string): Promise<User> => {
    await api.auth.register({ email, password, kennitala });
    // Auto-login after registration
    return await login(email, password);
  };

  const logout = async (): Promise<void> => {
    // Local state first: the UI is logged out whatever becomes of the request.
    api.clearTokens();
    awaitingRecovery.current = false;
    setUser(null);
    try {
      await api.auth.logout();
    } catch {
      // The refresh cookie is still in the browser. api.auth remembers that
      // and finishes the logout before it would restore a session.
    }
  };

  const getToken = (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  };

  const refreshUser = async (): Promise<User | null> => {
    if (api.isAuthenticated()) {
      const userData = await api.auth.getCurrentUser();
      setUser(userData);
      return userData;
    }
    return null;
  };

  const verifyEmail = async (code: string): Promise<boolean> => {
    const response = await api.auth.verifyEmail(code);
    return response.is_verified;
  };

  const resendVerification = async (): Promise<void> => {
    await api.auth.resendVerification();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        getToken,
        refreshUser,
        verifyEmail,
        resendVerification,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
