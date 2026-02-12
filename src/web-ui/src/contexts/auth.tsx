"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { api, User } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, kennitala: string) => Promise<User>;
  logout: () => void;
  getToken: () => string | null;
  refreshUser: () => Promise<User | null>;
  verifyEmail: (code: string) => Promise<boolean>;
  resendVerification: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const checkAuth = async () => {
      if (api.isAuthenticated()) {
        try {
          const userData = await api.auth.getCurrentUser();
          setUser(userData);
        } catch {
          api.clearTokens();
        }
      }
      setIsLoading(false);
    };

    checkAuth();

    // Listen for logout events (e.g., 401 responses)
    const handleLogout = () => {
      setUser(null);
    };

    window.addEventListener("auth:logout", handleLogout);
    return () => window.removeEventListener("auth:logout", handleLogout);
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    await api.auth.login(email, password);
    const userData = await api.auth.getCurrentUser();
    setUser(userData);
    return userData;
  };

  const register = async (email: string, password: string, kennitala: string): Promise<User> => {
    await api.auth.register({ email, password, kennitala });
    // Auto-login after registration
    return await login(email, password);
  };

  const logout = () => {
    api.clearTokens();
    setUser(null);
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
