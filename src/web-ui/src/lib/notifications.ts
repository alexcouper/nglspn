import type { NotificationGroup } from "@/lib/api";

export function buildDeepLink(group: NotificationGroup): string {
  const slugOrId = group.project.slug ?? group.project.id;
  if (group.kind === "article" && group.article_slug) {
    return `/projects/${slugOrId}/articles/${group.article_slug}`;
  }
  return `/projects/${slugOrId}?comment=${group.latest_comment_id}#discussions`;
}

export function groupKey(group: NotificationGroup): string | null {
  if (group.kind === "article") {
    return group.article_id ? `a:${group.article_id}` : null;
  }
  return group.root_discussion_id ? `d:${group.root_discussion_id}` : null;
}
