"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";
import { useNotifications, type NotificationDiffEvent } from "@/contexts/notifications";
import { useToasts } from "@/contexts/toasts";
import type { NotificationGroup } from "@/lib/api";
import { buildDeepLink } from "@/lib/notifications";
import { NotificationGroupItem } from "./NotificationGroupItem";

const DEBOUNCE_MS = 2 * 60 * 1000;
const TOAST_TTL_MS = 6_000;
// More than this many at once is a backlog, not news: one toast with the
// count, pointing at the notifications page, instead of a stack.
const MAX_INDIVIDUAL_TOASTS = 3;

export function NotificationToaster() {
  const t = useTranslations("notifications.toaster");
  const { subscribeDiff, markArticleRead } = useNotifications();
  const { showToast } = useToasts();
  const lastShownAtRef = useRef<Map<string, number>>(new Map());
  const router = useRouter();

  useEffect(() => {
    const openGroup = (group: NotificationGroup) => {
      if (group.kind === "article" && group.article_id) {
        void markArticleRead(group.article_id);
      }
      router.push(buildDeepLink(group));
    };

    return subscribeDiff(({ newlyActiveKeys, groupsByKey }: NotificationDiffEvent) => {
      // A toast raised in a background tab has expired by the time anyone
      // looks; the bell still carries the group.
      if (document.visibilityState === "hidden") return;

      const now = Date.now();
      const fresh: NotificationGroup[] = [];
      for (const key of newlyActiveKeys) {
        const group = groupsByKey.get(key);
        if (!group) continue;
        const last = lastShownAtRef.current.get(key);
        if (last && now - last < DEBOUNCE_MS) continue;
        lastShownAtRef.current.set(key, now);
        fresh.push(group);
      }

      if (fresh.length > MAX_INDIVIDUAL_TOASTS) {
        showToast({
          kind: "info",
          title: t("burst", { count: fresh.length }),
          ttlMs: TOAST_TTL_MS,
          onClick: () => router.push("/notifications"),
        });
        return;
      }

      for (const group of fresh) {
        showToast({
          kind: "info",
          title: "",
          ttlMs: TOAST_TTL_MS,
          onClick: () => openGroup(group),
          body: <NotificationGroupItem group={group} variant="toaster" />,
        });
      }
    });
  }, [subscribeDiff, showToast, router, markArticleRead, t]);

  return null;
}
