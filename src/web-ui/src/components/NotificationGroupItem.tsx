"use client";

import type { NotificationGroup } from "@/lib/api";
import { buildHeadline, relativeTime } from "@/lib/notifications";
import { EntityIcon } from "./EntityIcon";

type Variant = "popover" | "feed" | "toaster";

interface Props {
  group: NotificationGroup;
  variant: Variant;
  showUnreadSuffix?: boolean;
}

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

export function NotificationGroupItem({ group, variant, showUnreadSuffix }: Props) {
  const showTimestamp = variant !== "toaster";
  const suffix =
    showUnreadSuffix && group.unread_count > 1
      ? ` · ${group.unread_count} unread`
      : "";

  return (
    <>
      <EntityIcon
        imageUrl={group.article_image_url ?? group.project.image_url}
        title={group.article_title ?? group.project.title}
        size={ICON_SIZE[variant]}
      />
      <div className="flex-1 min-w-0">
        <div className={HEADLINE_TEXT[variant]}>{buildHeadline(group)}</div>
        <div className={BODY_TEXT[variant]}>{group.latest_body_excerpt}</div>
        {showTimestamp && (
          <div className="text-xs text-slate-400 mt-1">
            {relativeTime(group.latest_event_at)}
            {suffix}
          </div>
        )}
      </div>
    </>
  );
}
