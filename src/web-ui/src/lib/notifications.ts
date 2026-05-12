import type { NotificationGroup } from "@/lib/api";

export function buildDeepLink(group: NotificationGroup): string {
  const slugOrId = group.project.slug ?? group.project.id;
  return `/projects/${slugOrId}?comment=${group.latest_comment_id}#discussions`;
}

export function buildHeadline(group: NotificationGroup): string {
  const projectTitle = group.project.title;
  if (group.headline_kind === "started") {
    const author = group.actor_names[0] ?? "Someone";
    return `${author} started a discussion on ${projectTitle}`;
  }
  // replied
  const [first, ...rest] = group.actor_names;
  const others = rest.length;
  if (!first) return `New replies on ${projectTitle}`;
  if (others === 0) return `${first} replied on ${projectTitle}`;
  if (others === 1) return `${first} and 1 other replied on ${projectTitle}`;
  return `${first} and ${others} others replied on ${projectTitle}`;
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}
