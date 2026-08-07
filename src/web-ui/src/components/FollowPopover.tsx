"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChannelFollowState, FollowWithPreferences } from "@/lib/api/follows";
import { useToasts } from "@/contexts/toasts";
import { ChannelToggleList } from "@/components/ChannelToggleList";
import { useChannelToggle } from "@/hooks/useChannelToggle";

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

  const setChannels = useCallback(
    (update: (channels: ChannelFollowState[]) => ChannelFollowState[]) => {
      setFollow((prev) =>
        prev === null ? prev : { ...prev, channels: update(prev.channels) }
      );
    },
    []
  );

  const handleProjectUnfollowed = useCallback(() => {
    onUnfollow();
    onClose();
  }, [onUnfollow, onClose]);

  const toggleChannel = useChannelToggle({
    projectSlug,
    setChannels,
    onProjectUnfollowed: handleProjectUnfollowed,
  });

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
        {follow && (
          <ChannelToggleList
            channels={follow.channels}
            onToggle={toggleChannel}
          />
        )}
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
