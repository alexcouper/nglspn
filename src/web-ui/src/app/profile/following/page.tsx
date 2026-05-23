"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";
import type {
  FollowChannelPreference,
  FollowWithPreferences,
} from "@/lib/api/follows";
import { useToasts } from "@/contexts/toasts";

export default function FollowedProjectsPage() {
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
        setError("Couldn't load followed projects");
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading]);

  const handleToggle = async (
    projectSlug: string,
    channel: FollowChannelPreference,
    patch: { email_enabled?: boolean; in_app_enabled?: boolean }
  ) => {
    if (!follows) return;
    // Optimistic update.
    const next = { ...channel, ...patch };
    setFollows(
      follows.map((f) =>
        f.project_slug !== projectSlug
          ? f
          : {
              ...f,
              channels: f.channels.map((c) =>
                c.channel_id === channel.channel_id ? next : c
              ),
            }
      )
    );
    try {
      await api.follows.patchFollowChannel(
        projectSlug,
        channel.channel_id,
        patch
      );
    } catch {
      // Revert.
      setFollows(
        follows.map((f) =>
          f.project_slug !== projectSlug
            ? f
            : {
                ...f,
                channels: f.channels.map((c) =>
                  c.channel_id === channel.channel_id ? channel : c
                ),
              }
        )
      );
      showToast({
        kind: "error",
        title: "Couldn't update notification preference",
        ttlMs: 5_000,
      });
    }
  };

  const handleUnfollow = async (projectSlug: string) => {
    if (!follows) return;
    const previous = follows;
    // Optimistic remove.
    setFollows(follows.filter((f) => f.project_slug !== projectSlug));
    try {
      await api.follows.unfollow(projectSlug);
    } catch {
      setFollows(previous);
      showToast({
        kind: "error",
        title: "Couldn't unfollow",
        ttlMs: 5_000,
      });
    }
  };

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Following
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Channels and notifications for the projects you follow.
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
              You aren&apos;t following any projects yet.{" "}
              <Link href="/discover" className="text-accent hover:underline">
                Discover projects
              </Link>
              .
            </div>
          )}
          {follows && follows.length > 0 && (
            <ul className="space-y-3">
              {follows.map((follow) => (
                <FollowRow
                  key={follow.project_slug}
                  follow={follow}
                  onToggle={(channel, patch) =>
                    handleToggle(follow.project_slug, channel, patch)
                  }
                  onUnfollow={() => handleUnfollow(follow.project_slug)}
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
  onToggle: (
    channel: FollowChannelPreference,
    patch: { email_enabled?: boolean; in_app_enabled?: boolean }
  ) => void;
  onUnfollow: () => void;
}

function FollowRow({ follow, onToggle, onUnfollow }: FollowRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <li className="bg-white rounded-xl border border-border overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4">
        <button
          type="button"
          onClick={() => setIsExpanded((open) => !open)}
          className="flex items-center gap-3 flex-1 text-left"
          aria-expanded={isExpanded}
        >
          {follow.project_hero_image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={follow.project_hero_image_url}
              alt=""
              className="w-10 h-10 rounded-lg object-cover border border-border shrink-0"
            />
          )}
          <div className="min-w-0">
            <Link
              href={`/projects/${follow.project_slug}`}
              className="text-sm font-medium text-foreground hover:text-accent transition-colors block truncate"
              onClick={(e) => e.stopPropagation()}
            >
              {follow.project_title}
            </Link>
            <div className="text-xs text-muted-foreground">
              {follow.channels.length}{" "}
              {follow.channels.length === 1 ? "channel" : "channels"}
            </div>
          </div>
          <ChevronDownIcon
            className={`w-4 h-4 text-muted-foreground transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
          />
        </button>
        <button
          type="button"
          onClick={onUnfollow}
          className="ml-3 text-sm text-red-600 hover:text-red-700 transition-colors"
        >
          Unfollow
        </button>
      </div>
      {isExpanded && (
        <div className="border-t border-border px-5 py-3 space-y-2">
          {follow.channels.map((channel) => (
            <div
              key={channel.channel_id}
              className="flex items-center justify-between py-1"
            >
              <div className="text-sm text-foreground">
                {channel.channel_name}
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={channel.email_enabled}
                    onChange={(e) =>
                      onToggle(channel, { email_enabled: e.target.checked })
                    }
                  />
                  Email
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={channel.in_app_enabled}
                    onChange={(e) =>
                      onToggle(channel, { in_app_enabled: e.target.checked })
                    }
                  />
                  In-app
                </label>
              </div>
            </div>
          ))}
        </div>
      )}
    </li>
  );
}
