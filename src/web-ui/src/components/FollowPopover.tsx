"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  FollowChannelPreference,
  FollowWithPreferences,
} from "@/lib/api/follows";
import { useToasts } from "@/contexts/toasts";

interface FollowPopoverProps {
  projectSlug: string;
  onClose: () => void;
  onUnfollow: () => void;
}

export function FollowPopover({
  projectSlug,
  onClose,
  onUnfollow,
}: FollowPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState<FollowWithPreferences | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { showToast } = useToasts();

  useEffect(() => {
    let cancelled = false;
    api.follows
      .getFollowPreferences(projectSlug)
      .then((data) => {
        if (cancelled) return;
        setFollow(data);
      })
      .catch(() => {
        if (cancelled) return;
        setLoadError("Couldn't load preferences");
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlug]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const updateChannel = async (
    channel: FollowChannelPreference,
    patch: { email_enabled?: boolean; in_app_enabled?: boolean }
  ) => {
    if (!follow) return;
    // Optimistic update.
    const next = { ...channel, ...patch };
    setFollow({
      ...follow,
      channels: follow.channels.map((c) =>
        c.channel_id === channel.channel_id ? next : c
      ),
    });
    try {
      await api.follows.patchFollowChannel(
        projectSlug,
        channel.channel_id,
        patch
      );
    } catch {
      // Revert.
      setFollow({
        ...follow,
        channels: follow.channels.map((c) =>
          c.channel_id === channel.channel_id ? channel : c
        ),
      });
      showToast({
        kind: "error",
        title: "Couldn't update notification preference",
        ttlMs: 5_000,
      });
    }
  };

  const handleUnfollow = async () => {
    try {
      await api.follows.unfollow(projectSlug);
      onUnfollow();
      onClose();
    } catch {
      showToast({
        kind: "error",
        title: "Couldn't unfollow",
        ttlMs: 5_000,
      });
    }
  };

  return (
    <div
      ref={popoverRef}
      className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-border z-20"
    >
      <div className="px-3 py-2 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Notifications
      </div>
      <div className="p-1">
        {loadError && (
          <div className="px-3 py-3 text-sm text-muted-foreground">
            {loadError}
          </div>
        )}
        {!loadError && !follow && (
          <div className="px-3 py-3 text-sm text-muted-foreground">
            Loading…
          </div>
        )}
        {follow?.channels.map((channel) => (
          <div
            key={channel.channel_id}
            className="px-3 py-2 border-b border-border/50 last:border-0"
          >
            <div className="text-sm font-medium text-foreground mb-1">
              {channel.channel_name}
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={channel.email_enabled}
                  onChange={(e) =>
                    updateChannel(channel, { email_enabled: e.target.checked })
                  }
                />
                Email
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={channel.in_app_enabled}
                  onChange={(e) =>
                    updateChannel(channel, { in_app_enabled: e.target.checked })
                  }
                />
                In-app
              </label>
            </div>
          </div>
        ))}
      </div>
      <div className="px-3 py-2 border-t border-border">
        <button
          type="button"
          onClick={handleUnfollow}
          className="text-sm text-red-600 hover:text-red-700 transition-colors"
        >
          Unfollow
        </button>
      </div>
    </div>
  );
}
