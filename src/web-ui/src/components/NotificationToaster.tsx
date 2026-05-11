"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { NotificationGroup } from "@/lib/api";
import { useNotifications } from "@/contexts/notifications";
import { buildDeepLink } from "@/lib/notifications";
import { NotificationGroupItem } from "./NotificationGroupItem";

const DEBOUNCE_MS = 2 * 60 * 1000;
const TOAST_TTL_MS = 6_000;

interface ActiveToast {
  id: string;
  rootId: string;
  group: NotificationGroup;
}

export function NotificationToaster() {
  const { subscribeDiff } = useNotifications();
  const [toasts, setToasts] = useState<ActiveToast[]>([]);
  const lastShownAtRef = useRef<Map<string, number>>(new Map());
  const router = useRouter();

  useEffect(() => {
    return subscribeDiff(({ newlyActiveRoots, groupsByRoot }) => {
      const now = Date.now();
      const fresh: ActiveToast[] = [];
      for (const rootId of newlyActiveRoots) {
        const group = groupsByRoot.get(rootId);
        if (!group) continue;
        const last = lastShownAtRef.current.get(rootId);
        if (last && now - last < DEBOUNCE_MS) continue;
        lastShownAtRef.current.set(rootId, now);
        fresh.push({
          id: `${rootId}:${now}`,
          rootId,
          group,
        });
      }
      if (fresh.length === 0) return;
      setToasts((prev) => [...prev, ...fresh]);
      for (const toast of fresh) {
        window.setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== toast.id));
        }, TOAST_TTL_MS);
      }
    });
  }, [subscribeDiff]);

  const handleClick = (toast: ActiveToast) => {
    setToasts((prev) => prev.filter((t) => t.id !== toast.id));
    router.push(buildDeepLink(toast.group));
  };

  const handleDismiss = (toast: ActiveToast) => {
    setToasts((prev) => prev.filter((t) => t.id !== toast.id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="bg-white shadow-lg rounded-lg border border-slate-200 p-3 flex gap-3 items-start cursor-pointer hover:bg-slate-50 transition-colors"
          onClick={() => handleClick(toast)}
        >
          <NotificationGroupItem group={toast.group} variant="toaster" />
          <button
            type="button"
            aria-label="Dismiss"
            onClick={(event) => {
              event.stopPropagation();
              handleDismiss(toast);
            }}
            className="text-slate-400 hover:text-slate-600 ml-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
