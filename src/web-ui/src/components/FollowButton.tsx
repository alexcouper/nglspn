"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import { buildLoginPath } from "@/lib/auth-routing";
import { useAuth } from "@/contexts/auth";
import { FollowPopover } from "@/components/FollowPopover";

// What the button follows: a project by slug, or a person by id.
export type FollowTarget =
  | { kind: "project"; slug: string }
  | { kind: "user"; id: string };

interface FollowButtonProps {
  target: FollowTarget;
  // The server's answer where the page already has it (the profile carries
  // `is_followed`), which spares the probe below.
  initialFollowed?: boolean;
  // What an anonymous visitor sees: nothing (the default, as on a project
  // page), or a Follow button that sends them to log in and come back.
  whenAnonymous?: "hidden" | "login";
}

type FollowState = "loading" | "not-following" | "following";

export function FollowButton({
  target,
  initialFollowed,
  whenAnonymous = "hidden",
}: FollowButtonProps) {
  const t = useTranslations("projects.followButton");
  const router = useRouter();
  const pathname = usePathname();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const [state, setState] = useState<FollowState>(
    initialFollowed === undefined
      ? "loading"
      : initialFollowed
        ? "following"
        : "not-following",
  );
  const [isPending, setIsPending] = useState(false);
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  const targetKey = target.kind === "project" ? target.slug : target.id;

  // A project's state is probed through its preferences; a person's comes
  // from the profile, so there is nothing to ask for.
  useEffect(() => {
    if (isAuthLoading || !isAuthenticated) return;
    if (target.kind !== "project" || initialFollowed !== undefined) return;
    let cancelled = false;
    setState("loading");
    api.follows
      .getFollowPreferences(target.slug)
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
    // `targetKey` stands in for the target object, which callers rebuild per
    // render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetKey, target.kind, isAuthLoading, isAuthenticated, initialFollowed]);

  if (isAuthLoading) return null;
  if (!isAuthenticated) {
    if (whenAnonymous === "hidden") return null;
    return (
      <button
        type="button"
        onClick={() => router.push(buildLoginPath(pathname))}
        className={FOLLOW_CLASS}
      >
        {t("follow")}
      </button>
    );
  }

  if (state === "loading") {
    return (
      <div
        aria-hidden="true"
        className="h-[34px] w-[96px] bg-muted rounded-md animate-pulse"
      />
    );
  }

  const isFollowed = state === "following";

  const follow = () =>
    target.kind === "project"
      ? api.follows.follow(target.slug)
      : api.follows.followUser(target.id);
  const unfollow = () =>
    target.kind === "project"
      ? api.follows.unfollow(target.slug)
      : api.follows.unfollowUser(target.id);

  const handleClick = async () => {
    if (isPending) return;

    if (isFollowed) {
      // A project has channels to choose between, so Following opens the
      // popover. A person has one channel, so Following means unfollow.
      if (target.kind === "project") {
        setIsPopoverOpen((open) => !open);
        return;
      }
      setState("not-following");
      setIsPending(true);
      try {
        await unfollow();
      } catch {
        setState("following");
      } finally {
        setIsPending(false);
      }
      return;
    }

    setState("following");
    setIsPending(true);
    try {
      await follow();
    } catch {
      setState("not-following");
    } finally {
      setIsPending(false);
    }
  };

  const label = isFollowed ? t("following") : t("follow");
  const className = isFollowed ? FOLLOWING_CLASS : FOLLOW_CLASS;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        className={className}
        aria-pressed={isFollowed}
        aria-expanded={target.kind === "project" ? isPopoverOpen : undefined}
      >
        {label}
      </button>
      {isPopoverOpen && target.kind === "project" && (
        <FollowPopover
          projectSlug={target.slug}
          onClose={() => setIsPopoverOpen(false)}
          onUnfollow={() => setState("not-following")}
        />
      )}
    </div>
  );
}

const FOLLOW_CLASS =
  "text-sm font-medium bg-accent hover:bg-accent-hover text-white px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60";
const FOLLOWING_CLASS =
  "text-sm font-medium bg-white hover:bg-accent/5 text-accent border border-accent px-3.5 py-1.5 rounded-md transition-colors duration-150 disabled:opacity-60";
