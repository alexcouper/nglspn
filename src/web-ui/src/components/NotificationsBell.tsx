"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useNotifications } from "@/contexts/notifications";
import {
  buildDeepLink,
  buildHeadline,
  relativeTime,
} from "@/lib/notifications";

const POPOVER_LIMIT = 5;

export function NotificationsBell() {
  const { summary, groups, refreshGroups } = useNotifications();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    void refreshGroups();
  }, [open, refreshGroups]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const hasUnread = !!summary?.has_unread;
  const visibleGroups = groups.slice(0, POPOVER_LIMIT);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label="Notifications"
        onClick={() => setOpen((prev) => !prev)}
        className="relative p-1.5 -mr-1.5 text-slate-400 hover:text-white transition-colors"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {hasUnread && (
          <span
            data-testid="notification-bell-dot"
            className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500"
          />
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 mt-2 w-80 max-w-[90vw] bg-white shadow-lg rounded-lg border border-slate-200 z-50"
        >
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-900">Notifications</span>
            <Link
              href="/notifications"
              className="text-xs text-accent hover:underline"
              onClick={() => setOpen(false)}
            >
              See all
            </Link>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {visibleGroups.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-slate-500">
                You&apos;re all caught up
              </div>
            ) : (
              visibleGroups.map((group) => (
                <Link
                  key={group.root_discussion_id}
                  href={buildDeepLink(group)}
                  onClick={() => setOpen(false)}
                  className="flex gap-3 px-4 py-3 hover:bg-slate-50 transition-colors border-b border-slate-50 last:border-0"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded bg-slate-100 overflow-hidden">
                    {group.project.image_url ? (
                      <Image
                        src={group.project.image_url}
                        alt=""
                        width={40}
                        height={40}
                        className="w-full h-full object-cover"
                      />
                    ) : null}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-900 leading-snug">
                      {buildHeadline(group)}
                    </div>
                    <div className="text-xs text-slate-500 truncate mt-0.5">
                      {group.latest_body_excerpt}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {relativeTime(group.latest_event_at)}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
