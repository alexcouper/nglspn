"use client";

import type { ChannelFollowState } from "@/lib/api/follows";

interface ChannelToggleListProps {
  channels: ChannelFollowState[];
  onToggle: (channel: ChannelFollowState) => void;
}

/** The per-channel subscription checkboxes, shared by the follow popover and
 *  the following page so the two can't drift apart. */
export function ChannelToggleList({
  channels,
  onToggle,
}: ChannelToggleListProps) {
  return (
    <div role="group" aria-label="Channels">
      {channels.map((channel) => (
        <label
          key={channel.channel_id}
          className="flex items-center gap-2 px-3 py-2 border-b border-border/50 last:border-0 cursor-pointer text-sm"
        >
          <input
            type="checkbox"
            checked={channel.followed}
            onChange={() => onToggle(channel)}
          />
          <span className="text-foreground">{channel.channel_name}</span>
        </label>
      ))}
    </div>
  );
}
