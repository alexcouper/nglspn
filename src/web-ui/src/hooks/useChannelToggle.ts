"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import type { ChannelFollowState } from "@/lib/api/follows";
import { useToasts } from "@/contexts/toasts";

type ChannelsUpdater = (
  update: (channels: ChannelFollowState[]) => ChannelFollowState[]
) => void;

interface UseChannelToggleOptions {
  projectSlug: string;
  /** Applies a functional update to whichever state holds the channel list. */
  setChannels: ChannelsUpdater;
  /** Called when unfollowing the last channel removed the project follow. */
  onProjectUnfollowed: () => void;
}

/**
 * Optimistic follow/unfollow of a single channel.
 *
 * Every write is a functional update, so two toggles in flight at once can't
 * clobber each other and a failure rolls back only its own channel.
 */
export function useChannelToggle({
  projectSlug,
  setChannels,
  onProjectUnfollowed,
}: UseChannelToggleOptions) {
  const { showToast } = useToasts();

  return useCallback(
    async (channel: ChannelFollowState) => {
      const followed = !channel.followed;
      const write = (value: boolean) =>
        setChannels((channels) =>
          channels.map((c) =>
            c.channel_id === channel.channel_id ? { ...c, followed: value } : c
          )
        );

      write(followed);
      try {
        if (followed) {
          await api.follows.followChannel(projectSlug, channel.channel_id);
          return;
        }
        const state = await api.follows.unfollowChannel(
          projectSlug,
          channel.channel_id
        );
        if (!state.is_followed) onProjectUnfollowed();
      } catch {
        write(channel.followed);
        showToast({
          kind: "error",
          title: "Couldn't update channel",
          ttlMs: 5_000,
        });
      }
    },
    [projectSlug, setChannels, onProjectUnfollowed, showToast]
  );
}
