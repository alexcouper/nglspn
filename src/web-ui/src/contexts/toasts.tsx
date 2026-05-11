"use client";

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

export type ToastKind = "info" | "warning" | "error";

export interface ToastInput {
  kind?: ToastKind;
  title: string;
  description?: string;
  ttlMs?: number;
  onClick?: () => void;
  body?: ReactNode;
}

export interface Toast extends ToastInput {
  id: string;
}

const DEFAULT_TTL_MS = 6_000;

interface ToastsContextValue {
  toasts: Toast[];
  showToast: (toast: ToastInput) => string;
  dismissToast: (id: string) => void;
}

const ToastsContext = createContext<ToastsContextValue | undefined>(undefined);

export function ToastsProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (input: ToastInput) => {
      counterRef.current += 1;
      const id = `t${counterRef.current}:${Date.now()}`;
      const toast: Toast = { ...input, id };
      setToasts((prev) => [...prev, toast]);
      const ttl = input.ttlMs ?? DEFAULT_TTL_MS;
      window.setTimeout(() => dismissToast(id), ttl);
      return id;
    },
    [dismissToast]
  );

  const value = useMemo<ToastsContextValue>(
    () => ({ toasts, showToast, dismissToast }),
    [toasts, showToast, dismissToast]
  );

  return (
    <ToastsContext.Provider value={value}>{children}</ToastsContext.Provider>
  );
}

export function useToasts(): ToastsContextValue {
  const ctx = useContext(ToastsContext);
  if (ctx === undefined) {
    throw new Error("useToasts must be used within ToastsProvider");
  }
  return ctx;
}
