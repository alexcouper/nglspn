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
  const { subscribeDiff, markArticleRead } = useNotifications();
  const { showToast } = useToasts();
  const lastShownAtRef = useRef<Map<string, number>>(new Map());
  const router = useRouter();

  useEffect(() => {
    return subscribeDiff(({ newlyActiveKeys, groupsByKey }) => {
      const now = Date.now();
      for (const key of newlyActiveKeys) {
        const group = groupsByKey.get(key);
        if (!group) continue;
        const last = lastShownAtRef.current.get(key);
        if (last && now - last < DEBOUNCE_MS) continue;
        lastShownAtRef.current.set(key, now);
        showToast({
          kind: "info",
          title: "",
          ttlMs: TOAST_TTL_MS,
          onClick: () => {
            if (group.kind === "article" && group.article_id) {
              void markArticleRead(group.article_id);
            }
            router.push(buildDeepLink(group));
          },
          body: <NotificationGroupItem group={group} variant="toaster" />,
        });
      }
    });
  }, [subscribeDiff, showToast, router, markArticleRead]);

  return null;
}
