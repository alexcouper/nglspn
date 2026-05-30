"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  ChannelFollowState,
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

  const toggleChannel = async (channel: ChannelFollowState) => {
    if (!follow) return;
    const next: ChannelFollowState = { ...channel, followed: !channel.followed };
    // Optimistic update.
    setFollow({
      ...follow,
      channels: follow.channels.map((c) =>
        c.channel_id === channel.channel_id ? next : c
      ),
    });
    try {
      if (next.followed) {
        await api.follows.followChannel(projectSlug, channel.channel_id);
      } else {
        await api.follows.unfollowChannel(projectSlug, channel.channel_id);
      }
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
        title: "Couldn't update channel",
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
        Channels
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
          <label
            key={channel.channel_id}
            className="flex items-center gap-2 px-3 py-2 border-b border-border/50 last:border-0 cursor-pointer text-sm"
          >
            <input
              type="checkbox"
              checked={channel.followed}
              onChange={() => toggleChannel(channel)}
            />
            <span className="text-foreground">{channel.channel_name}</span>
          </label>
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
