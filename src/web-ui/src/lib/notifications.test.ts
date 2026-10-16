import { describe, expect, it } from "vitest";
import type { NotificationGroup } from "@/lib/api";
import { buildDeepLink } from "./notifications";

function articleGroup(overrides: Partial<NotificationGroup> = {}): NotificationGroup {
  return {
    kind: "article",
    project: { id: "p-1", slug: "hverfid", title: "Hverfið", image_url: null },
    author: { id: "u-1", name: "Ada Lovelace", avatar_url: null },
    article_id: "a-1",
    article_slug: "hello",
    article_title: "Hello",
    latest_body_excerpt: "",
    latest_event_at: "2026-10-01T09:00:00Z",
    unread_count: 1,
    ...overrides,
  } as NotificationGroup;
}

describe("buildDeepLink", () => {
  it("sends a project article's group to the article under its project", () => {
    expect(buildDeepLink(articleGroup())).toBe("/projects/hverfid/articles/hello");
  });

  it("sends an author-owned article's group to the article under the author", () => {
    expect(buildDeepLink(articleGroup({ project: null }))).toBe("/users/u-1/articles/hello");
  });
});
