"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth";
import { FollowPopover } from "@/components/FollowPopover";

interface FollowButtonProps {
  projectSlug: string;
  initialIsFollowed: boolean;
}

export function FollowButton({
  projectSlug,
  initialIsFollowed,
}: FollowButtonProps) {
  const { isAuthenticated } = useAuth();
  const [isFollowed, setIsFollowed] = useState(initialIsFollowed);
  const [isPending, setIsPending] = useState(false);
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  if (!isAuthenticated) {
    return null;
  }

  const handleClick = async () => {
    if (isPending) return;

    if (isFollowed) {
      // Toggle popover; the popover handles unfollow.
      setIsPopoverOpen((open) => !open);
      return;
    }

    // Not-yet-followed: instantly follow (optimistic).
    setIsFollowed(true);
    setIsPending(true);
    try {
      await api.follows.follow(projectSlug);
    } catch {
      setIsFollowed(false);
    } finally {
      setIsPending(false);
    }
  };

  const label = isFollowed ? "Following" : "Follow";
  const className = isFollowed
    ? "text-sm font-medium bg-white hover:bg-accent/5 text-accent border border-accent px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60"
    : "text-sm font-medium bg-accent hover:bg-accent-hover text-white px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60";

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        className={className}
        aria-pressed={isFollowed}
        aria-expanded={isPopoverOpen}
      >
        {label}
      </button>
      {isPopoverOpen && (
        <FollowPopover
          projectSlug={projectSlug}
          onClose={() => setIsPopoverOpen(false)}
          onUnfollow={() => setIsFollowed(false)}
        />
      )}
    </div>
  );
}
