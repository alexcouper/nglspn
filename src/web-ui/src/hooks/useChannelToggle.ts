"use client";

import { useCallback } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { ChannelFollowState } from "@/lib/api/follows";
import type { FollowTarget } from "@/components/FollowButton";
import { useToasts } from "@/contexts/toasts";

type ChannelsUpdater = (
  update: (channels: ChannelFollowState[]) => ChannelFollowState[]
) => void;

interface UseChannelToggleOptions {
  /** Whose channel list this is: a followed project, or a followed person. */
  target: FollowTarget;
  /** Applies a functional update to whichever state holds the channel list. */
  setChannels: ChannelsUpdater;
  /** Called when unfollowing the last channel removed the follow itself. */
  onUnfollowed: () => void;
}

/**
 * Optimistic follow/unfollow of a single channel.
 *
 * Every write is a functional update, so two toggles in flight at once can't
 * clobber each other and a failure rolls back only its own channel.
 */
export function useChannelToggle({
  target,
  setChannels,
  onUnfollowed,
}: UseChannelToggleOptions) {
  const t = useTranslations("projects.channelToggle");
  const { showToast } = useToasts();
  const targetKey = target.kind === "project" ? target.slug : target.id;

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
          if (target.kind === "project") {
            await api.follows.followChannel(target.slug, channel.channel_id);
          } else {
            await api.follows.followUserChannel(target.id, channel.channel_id);
          }
          return;
        }
        const state =
          target.kind === "project"
            ? await api.follows.unfollowChannel(target.slug, channel.channel_id)
            : await api.follows.unfollowUserChannel(target.id, channel.channel_id);
        if (!state.is_followed) onUnfollowed();
      } catch {
        write(channel.followed);
        showToast({
          kind: "error",
          title: t("updateFailed"),
          ttlMs: 5_000,
        });
      }
    },
    // `targetKey` stands in for the target object, which callers rebuild per
    // render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [targetKey, target.kind, setChannels, onUnfollowed, showToast, t]
  );
}
