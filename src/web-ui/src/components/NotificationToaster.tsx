"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useNotifications } from "@/contexts/notifications";
import { useToasts } from "@/contexts/toasts";
import { buildDeepLink } from "@/lib/notifications";
import { NotificationGroupItem } from "./NotificationGroupItem";

const DEBOUNCE_MS = 2 * 60 * 1000;
const TOAST_TTL_MS = 6_000;

export function NotificationToaster() {
  const { subscribeDiff } = useNotifications();
  const { showToast } = useToasts();
  const lastShownAtRef = useRef<Map<string, number>>(new Map());
  const router = useRouter();

  useEffect(() => {
    return subscribeDiff(({ newlyActiveRoots, groupsByRoot }) => {
      const now = Date.now();
      for (const rootId of newlyActiveRoots) {
        const group = groupsByRoot.get(rootId);
        if (!group) continue;
        const last = lastShownAtRef.current.get(rootId);
        if (last && now - last < DEBOUNCE_MS) continue;
        lastShownAtRef.current.set(rootId, now);
        showToast({
          kind: "info",
          title: "",
          ttlMs: TOAST_TTL_MS,
          onClick: () => router.push(buildDeepLink(group)),
          body: <NotificationGroupItem group={group} variant="toaster" />,
        });
      }
    });
  }, [subscribeDiff, showToast, router]);

  return null;
}
