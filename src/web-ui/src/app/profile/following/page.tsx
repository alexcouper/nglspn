"use client";

import { useCallback, useEffect, useId, useState } from "react";
import Link from "next/link";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useChannelToggle } from "@/hooks/useChannelToggle";
import { api } from "@/lib/api";
import type {
  ChannelFollowState,
  FollowWithPreferences,
} from "@/lib/api/follows";
import { Avatar } from "@/components/Avatar";
import { ChannelToggleList } from "@/components/ChannelToggleList";
import type { FollowTarget } from "@/components/FollowButton";
import { useToasts } from "@/contexts/toasts";

// One key per row, whichever kind it is.
export function followKey(follow: FollowWithPreferences): string {
  return follow.target === "user"
    ? `user:${follow.user_id ?? ""}`
    : `project:${follow.project_slug ?? ""}`;
}

function targetOf(follow: FollowWithPreferences): FollowTarget {
  return follow.target === "user"
    ? { kind: "user", id: follow.user_id ?? "" }
    : { kind: "project", slug: follow.project_slug ?? "" };
}

async function unfollowTarget(target: FollowTarget): Promise<void> {
  if (target.kind === "project") await api.follows.unfollow(target.slug);
  else await api.follows.unfollowUser(target.id);
}

export default function FollowedProjectsPage() {
  const t = useTranslations("profile.following");
  const { isLoading: authLoading } = useRequireAuth();
  const { showToast } = useToasts();
  const [follows, setFollows] = useState<FollowWithPreferences[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    api.follows
      .listFollows()
      .then((data) => {
        if (cancelled) return;
        setFollows(data);
      })
      .catch(() => {
        if (cancelled) return;
        setError(t("errors.loadFailed"));
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, t]);

  const removeRow = useCallback((key: string) => {
    setFollows((prev) =>
      prev === null ? prev : prev.filter((f) => followKey(f) !== key)
    );
  }, []);

  const handleUnfollow = async (follow: FollowWithPreferences) => {
    if (!follows) return;
    const previous = follows;
    // Optimistic remove.
    removeRow(followKey(follow));
    try {
      await unfollowTarget(targetOf(follow));
    } catch {
      setFollows(previous);
      showToast({
        kind: "error",
        title: t("errors.unfollowFailed"),
        ttlMs: 5_000,
      });
    }
  };

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            {t("title")}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t("intro")}
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          {!error && follows === null && (
            <div className="bg-white rounded-xl border border-border p-5">
              <div className="skeleton h-6 w-1/3 mb-3" />
              <div className="skeleton h-6 w-1/2" />
            </div>
          )}
          {follows?.length === 0 && (
            <div className="bg-white rounded-xl border border-border p-6 text-sm text-muted-foreground">
              {t.rich("empty", {
                link: (chunks) => (
                  <Link href="/projects" className="text-accent hover:underline">
                    {chunks}
                  </Link>
                ),
              })}
            </div>
          )}
          {follows && follows.length > 0 && (
            <ul className="space-y-3">
              {follows.map((follow) => (
                <FollowRow
                  key={followKey(follow)}
                  follow={follow}
                  onUnfollow={() => handleUnfollow(follow)}
                  onUnfollowed={removeRow}
                />
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}

interface FollowRowProps {
  follow: FollowWithPreferences;
  onUnfollow: () => void;
  onUnfollowed: (key: string) => void;
}

function FollowRow({ follow, onUnfollow, onUnfollowed }: FollowRowProps) {
  const t = useTranslations("profile.following");
  const [isExpanded, setIsExpanded] = useState(false);
  // The list is fetched once, so channel state lives here and is mutated in
  // place rather than refetched.
  const [channels, setChannels] = useState<ChannelFollowState[]>(
    follow.channels
  );
  const panelId = useId();
  const followedCount = channels.filter((c) => c.followed).length;
  const key = followKey(follow);
  const isPerson = follow.target === "user";
  const title = isPerson ? (follow.user_name ?? "") : (follow.project_title ?? "");
  const href = isPerson
    ? `/users/${follow.user_id}`
    : `/projects/${follow.project_slug}`;

  const handleUnfollowed = useCallback(() => {
    onUnfollowed(key);
  }, [onUnfollowed, key]);

  const toggleChannel = useChannelToggle({
    target: targetOf(follow),
    setChannels,
    onUnfollowed: handleUnfollowed,
  });

  return (
    <li
      className="bg-white rounded-xl border border-border overflow-hidden"
      data-testid={`follow-row-${follow.target}`}
    >
      <div className="flex items-center gap-3 px-5 py-4">
        {isPerson ? (
          <Avatar
            src={follow.user_avatar_url}
            firstName={title}
            lastName=""
            size={40}
          />
        ) : (
          follow.project_hero_image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={follow.project_hero_image_url}
              alt=""
              className="w-10 h-10 rounded-lg object-cover border border-border shrink-0"
            />
          )
        )}
        <div className="min-w-0 flex-1">
          <Link
            href={href}
            className="text-sm font-medium text-foreground hover:text-accent transition-colors block truncate"
          >
            {title}
          </Link>
          <div className="text-xs text-muted-foreground">
            {isPerson && channels.length === 0
              ? t("noArticlesYet")
              : t("channelCount", { followed: followedCount, total: channels.length })}
          </div>
        </div>
        {channels.length > 0 && (
          <button
            type="button"
            onClick={() => setIsExpanded((open) => !open)}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors"
            aria-expanded={isExpanded}
            aria-controls={panelId}
            aria-label={t("channelsFor", { title })}
          >
            <ChevronDownIcon
              className={`w-4 h-4 transition-transform ${
                isExpanded ? "rotate-180" : ""
              }`}
            />
          </button>
        )}
        <button
          type="button"
          onClick={onUnfollow}
          className="ml-1 text-sm text-red-600 hover:text-red-700 transition-colors"
        >
          {t("unfollow")}
        </button>
      </div>
      {isExpanded && (
        <div id={panelId} className="border-t border-border px-2 py-1">
          <ChannelToggleList channels={channels} onToggle={toggleChannel} />
        </div>
      )}
    </li>
  );
}
