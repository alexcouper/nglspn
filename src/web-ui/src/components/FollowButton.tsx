"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import { useAuth } from "@/contexts/auth";
import { FollowPopover } from "@/components/FollowPopover";

interface FollowButtonProps {
  projectSlug: string;
}

type FollowState = "loading" | "not-following" | "following";

export function FollowButton({ projectSlug }: FollowButtonProps) {
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const [state, setState] = useState<FollowState>("loading");
  const [isPending, setIsPending] = useState(false);
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  useEffect(() => {
    if (isAuthLoading || !isAuthenticated) return;
    let cancelled = false;
    setState("loading");
    api.follows
      .getFollowPreferences(projectSlug)
      .then(() => {
        if (!cancelled) setState("following");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setState("not-following");
        } else {
          // Network/server error: assume not-following so the user can still
          // try to act; a failed follow click will surface its own error.
          setState("not-following");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlug, isAuthLoading, isAuthenticated]);

  if (isAuthLoading) return null;
  if (!isAuthenticated) return null;

  if (state === "loading") {
    return (
      <div
        aria-hidden="true"
        className="h-[34px] w-[96px] bg-muted rounded-md animate-pulse"
      />
    );
  }

  const isFollowed = state === "following";

  const handleClick = async () => {
    if (isPending) return;

    if (isFollowed) {
      setIsPopoverOpen((open) => !open);
      return;
    }

    setState("following");
    setIsPending(true);
    try {
      await api.follows.follow(projectSlug);
    } catch {
      setState("not-following");
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
          onUnfollow={() => setState("not-following")}
        />
      )}
    </div>
  );
}
