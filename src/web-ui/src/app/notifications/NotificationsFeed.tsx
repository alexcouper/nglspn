"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useNotifications } from "@/contexts/notifications";
import {
  buildDeepLink,
  buildHeadline,
  relativeTime,
} from "@/lib/notifications";

export function NotificationsFeed() {
  const { isReady } = useRequireAuth();
  const { groups, loadingGroups, refreshGroups, markThreadRead } = useNotifications();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isReady) return;
    void refreshGroups();
  }, [isReady, refreshGroups]);

  if (!isReady) return null;

  const toggle = (rootId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(rootId)) next.delete(rootId);
      else next.add(rootId);
      return next;
    });
  };

  const handleMarkSelected = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    try {
      await Promise.all(
        Array.from(selected).map((rootId) => markThreadRead(rootId))
      );
      setSelected(new Set());
      await refreshGroups();
    } finally {
      setBusy(false);
    }
  };

  const handleMarkAll = async () => {
    if (groups.length === 0) return;
    setBusy(true);
    try {
      await Promise.all(
        groups.map((g) => markThreadRead(g.root_discussion_id))
      );
      setSelected(new Set());
      await refreshGroups();
    } finally {
      setBusy(false);
    }
  };

  if (groups.length === 0) {
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
          disabled={busy || groups.length === 0}
          className="px-3 py-1.5 text-xs font-medium border border-border rounded-md text-foreground hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Mark all as read
        </button>
      </div>
      <div className="bg-white rounded-xl border border-border divide-y divide-slate-100 overflow-hidden">
        {groups.map((group) => {
          const isSelected = selected.has(group.root_discussion_id);
          return (
            <div
              key={group.root_discussion_id}
              className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggle(group.root_discussion_id)}
                className="mt-1.5 h-4 w-4 rounded border-slate-300"
                aria-label="Select notification"
              />
              <Link
                href={buildDeepLink(group)}
                className="flex flex-1 min-w-0 gap-3"
              >
                <div className="flex-shrink-0 w-12 h-12 rounded bg-slate-100 overflow-hidden">
                  {group.project.image_url ? (
                    <Image
                      src={group.project.image_url}
                      alt=""
                      width={48}
                      height={48}
                      className="w-full h-full object-cover"
                    />
                  ) : null}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-foreground leading-snug">
                    {buildHeadline(group)}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                    {group.latest_body_excerpt}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {relativeTime(group.latest_event_at)}
                    {group.unread_count > 1 ? ` · ${group.unread_count} unread` : ""}
                  </div>
                </div>
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
