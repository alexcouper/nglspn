"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useNotifications } from "@/contexts/notifications";
import { buildDeepLink, groupKey } from "@/lib/notifications";
import { NotificationGroupItem } from "@/components/NotificationGroupItem";
import type { NotificationGroup } from "@/lib/api";

export function NotificationsFeed() {
  const { isReady } = useRequireAuth();
  const {
    groups,
    refreshGroups,
    markThreadRead,
    markArticleRead,
    markAllRead,
  } = useNotifications();
  const visibleGroups = groups.filter(
    (g): g is NotificationGroup => groupKey(g) !== null,
  );
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isReady) return;
    void refreshGroups();
  }, [isReady, refreshGroups]);

  if (!isReady) return null;

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const markGroup = (group: NotificationGroup): Promise<void> => {
    if (group.kind === "article" && group.article_id) {
      return markArticleRead(group.article_id);
    }
    if (group.root_discussion_id) {
      return markThreadRead(group.root_discussion_id);
    }
    return Promise.resolve();
  };

  const handleMarkSelected = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    try {
      const byKey = new Map(visibleGroups.map((g) => [groupKey(g)!, g]));
      await Promise.all(
        Array.from(selected)
          .map((key) => byKey.get(key))
          .filter((g): g is NotificationGroup => Boolean(g))
          .map(markGroup),
      );
      setSelected(new Set());
      await refreshGroups();
    } finally {
      setBusy(false);
    }
  };

  const handleMarkAll = async () => {
    if (visibleGroups.length === 0) return;
    setBusy(true);
    try {
      await markAllRead();
      setSelected(new Set());
      await refreshGroups();
    } finally {
      setBusy(false);
    }
  };

  if (visibleGroups.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-border px-6 py-16 text-center">
        <h2 className="text-lg font-medium text-foreground">
          You&apos;re all caught up
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          No unread notifications.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleMarkSelected}
          disabled={busy || selected.size === 0}
          className="px-3 py-1.5 text-xs font-medium border border-border rounded-md text-foreground hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Mark selected as read
        </button>
        <button
          type="button"
          onClick={handleMarkAll}
          disabled={busy || visibleGroups.length === 0}
          className="px-3 py-1.5 text-xs font-medium border border-border rounded-md text-foreground hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Mark all as read
        </button>
      </div>
      <div className="bg-white rounded-xl border border-border divide-y divide-slate-100 overflow-hidden">
        {visibleGroups.map((group) => {
          const key = groupKey(group)!;
          const isSelected = selected.has(key);
          return (
            <div
              key={key}
              className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggle(key)}
                className="mt-1.5 h-4 w-4 rounded border-slate-300"
                aria-label="Select notification"
              />
              <Link
                href={buildDeepLink(group)}
                onClick={() => {
                  // Clear optimistically — handles the article-stale case
                  // where the render page would 404 and never get to mark
                  // itself read. Idempotent for the happy path.
                  if (group.kind === "article" && group.article_id) {
                    void markArticleRead(group.article_id);
                  }
                }}
                className="flex flex-1 min-w-0 gap-3"
              >
                <NotificationGroupItem
                  group={group}
                  variant="feed"
                  showUnreadSuffix
                />
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
