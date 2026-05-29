"use client";

import type { Channel } from "@/lib/api";

interface Props {
  channels: Channel[];
  value: string;
  onChange: (channelId: string) => void;
  disabled?: boolean;
}

export function ChannelDropdown({
  channels,
  value,
  onChange,
  disabled = false,
}: Props) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className="whitespace-nowrap">Channel</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || channels.length === 0}
        className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12"
      >
        {channels.length === 0 ? (
          <option value="">No channels available</option>
        ) : (
          channels.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))
        )}
      </select>
    </label>
  );
}
