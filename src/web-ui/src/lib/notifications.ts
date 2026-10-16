import type { NotificationGroup } from "@/lib/api";

// Where a group leads: an article at its public address — under its project,
// or under its author for one published under their own name — or the
// discussion on its project.
export function buildDeepLink(group: NotificationGroup): string {
  if (group.kind === "article" && group.article_slug) {
    if (group.project) {
      return `/projects/${group.project.slug ?? group.project.id}/articles/${group.article_slug}`;
    }
    if (group.author) {
      return `/users/${group.author.id}/articles/${group.article_slug}`;
    }
  }
  if (!group.project) return "/notifications";
  const slugOrId = group.project.slug ?? group.project.id;
  return `/projects/${slugOrId}?comment=${group.latest_comment_id}#discussions`;
}

export function groupKey(group: NotificationGroup): string | null {
  if (group.kind === "article") {
    return group.article_id ? `a:${group.article_id}` : null;
  }
  return group.root_discussion_id ? `d:${group.root_discussion_id}` : null;
}
