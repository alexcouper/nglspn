"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth";

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

  if (!isAuthenticated) {
    return null;
  }

  const handleClick = async () => {
    if (isPending) return;
    const next = !isFollowed;
    // Optimistic toggle.
    setIsFollowed(next);
    setIsPending(true);
    try {
      if (next) {
        await api.follows.follow(projectSlug);
      } else {
        await api.follows.unfollow(projectSlug);
      }
    } catch {
      // Revert on failure.
      setIsFollowed(!next);
    } finally {
      setIsPending(false);
    }
  };

  const label = isFollowed ? "Following" : "Follow";
  const className = isFollowed
    ? "text-sm font-medium bg-white hover:bg-accent/5 text-accent border border-accent px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60"
    : "text-sm font-medium bg-accent hover:bg-accent-hover text-white px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60";

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isPending}
      className={className}
      aria-pressed={isFollowed}
    >
      {label}
    </button>
  );
}
