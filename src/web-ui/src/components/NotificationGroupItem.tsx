"use client";

import { useTranslations } from "next-intl";
import type { NotificationGroup } from "@/lib/api";
import { EntityIcon } from "./EntityIcon";

type Variant = "popover" | "feed" | "toaster";

interface Props {
  group: NotificationGroup;
  variant: Variant;
  showUnreadSuffix?: boolean;
}

type GroupItemTranslator = ReturnType<typeof useTranslations<"notifications.groupItem">>;

const ICON_SIZE: Record<Variant, number> = {
  popover: 40,
  feed: 48,
  toaster: 36,
};

const HEADLINE_TEXT: Record<Variant, string> = {
  popover: "text-sm text-slate-900 leading-snug",
  feed: "text-sm text-foreground leading-snug",
  toaster: "text-sm text-slate-900 leading-snug",
};

const BODY_TEXT: Record<Variant, string> = {
  popover: "text-xs text-slate-500 truncate mt-0.5",
  feed: "text-xs text-muted-foreground mt-0.5 line-clamp-2",
  toaster: "text-xs text-slate-500 truncate mt-0.5",
};

// Who the group is about: the project, or for an author-owned article the
// author. A discussion group always has a project.
function headOf(group: NotificationGroup): { name: string; imageUrl: string | null } {
  if (group.project) {
    return { name: group.project.title, imageUrl: group.project.image_url ?? null };
  }
  return { name: group.author?.name ?? "", imageUrl: group.author?.avatar_url ?? null };
}

function headline(group: NotificationGroup, t: GroupItemTranslator): string {
  const project = headOf(group).name;
  if (group.kind === "article") {
    const title = group.article_title ?? t("headline.untitledArticle");
    // A person's channel is a placeholder, so only a project's is named.
    const channel = group.project ? group.channel_name : null;
    return channel
      ? t("headline.articlePublishedInChannel", { project, title, channel })
      : t("headline.articlePublished", { project, title });
  }
  if (group.headline_kind === "started") {
    const author = group.actor_names[0] ?? t("headline.someone");
    return t("headline.discussionStarted", { author, project });
  }
  // replied
  const [first, ...rest] = group.actor_names;
  if (!first) return t("headline.newReplies", { project });
  if (rest.length === 0) return t("headline.replied", { name: first, project });
  return t("headline.repliedWithOthers", { name: first, count: rest.length, project });
}

function relativeTime(iso: string, t: GroupItemTranslator): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return t("relative.justNow");
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return t("relative.minutesAgo", { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("relative.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t("relative.daysAgo", { count: days });
  const weeks = Math.floor(days / 7);
  return t("relative.weeksAgo", { count: weeks });
}

export function NotificationGroupItem({ group, variant, showUnreadSuffix }: Props) {
  const t = useTranslations("notifications.groupItem");
  const showTimestamp = variant !== "toaster";
  const time = relativeTime(group.latest_event_at, t);
  const timestamp =
    showUnreadSuffix && group.unread_count > 1
      ? t("timestampWithUnread", { time, count: group.unread_count })
      : time;

  return (
    <>
      <EntityIcon
        imageUrl={group.article_image_url ?? headOf(group).imageUrl}
        title={group.article_title ?? headOf(group).name}
        size={ICON_SIZE[variant]}
      />
      <div className="flex-1 min-w-0">
        <div className={HEADLINE_TEXT[variant]}>{headline(group, t)}</div>
        <div className={BODY_TEXT[variant]}>{group.latest_body_excerpt}</div>
        {showTimestamp && (
          <div className="text-xs text-slate-400 mt-1">{timestamp}</div>
        )}
      </div>
    </>
  );
}
