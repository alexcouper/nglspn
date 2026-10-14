import { describe, expect, it } from "vitest";

import type { Article, ArticleListItem, FeedEntry, Project } from "@/lib/api";

import { buildOnward } from "./onward";

const UPDATES = { id: "ch-updates", name: "Updates" };
const PRODUCT = { id: "ch-product", name: "Product updates" };

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "p-1",
    slug: "hot-spring-finder",
    title: "Hot Spring Finder",
    ...overrides,
  } as Project;
}

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "a-current",
    title: "We mapped 94 unmarked hot springs",
    channel: UPDATES,
    ...overrides,
  } as Article;
}

function sibling(overrides: Partial<ArticleListItem> = {}): ArticleListItem {
  return {
    id: "a-other",
    title: "Offline tiles",
    summary: "A storage problem, not a network one.",
    slug: "offline-tiles",
    state: "published",
    published_at: "2026-10-14T09:00:00Z",
    channel: UPDATES,
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  } as ArticleListItem;
}

function feedEntry(overrides: Record<string, unknown> = {}): FeedEntry {
  return {
    id: "f-1",
    kind: "article_published",
    occurred_at: "2026-10-01T09:00:00Z",
    is_pinned: false,
    project: null,
    discussion: null,
    article: {
      id: "a-elsewhere",
      slug: "counting-cyclists",
      title: "Counting cyclists with a doorbell camera",
      summary: "A €30 camera and four weekends.",
      channel_name: "Updates",
      project_slug: "reykjavik-bikes",
      project_title: "Reykjavik Bikes",
      listing_image_url: null,
      listing_crop: null,
    },
    ...overrides,
  } as FeedEntry;
}

function build(overrides: Parameters<typeof buildOnward>[0] | object = {}) {
  return buildOnward({
    project: project(),
    article: article(),
    siblings: [],
    feed: null,
    ...overrides,
  } as Parameters<typeof buildOnward>[0]);
}

describe("buildOnward", () => {
  it("leads with the nearest article in the same channel", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-newer", title: "Newer", published_at: "2026-10-14T09:00:00Z" }),
        sibling({ id: "a-older", title: "Older", published_at: "2026-09-01T09:00:00Z" }),
      ],
    });

    expect(result?.heading).toBe("More in Updates");
    expect(result?.lead.title).toBe("Newer");
  });

  it("falls back to the previous article when this is the newest in the channel", () => {
    const result = build({
      siblings: [sibling({ id: "a-older", title: "Older", published_at: "2026-09-01T09:00:00Z" })],
    });

    // Same heading as when a newer one exists: only the card changes.
    expect(result?.heading).toBe("More in Updates");
    expect(result?.lead.title).toBe("Older");
  });

  it("names the project instead when the channel has nothing else", () => {
    const result = build({
      siblings: [sibling({ id: "a-other-channel", title: "Winter map", channel: PRODUCT })],
    });

    expect(result?.heading).toBe("More from Hot Spring Finder");
    expect(result?.lead.title).toBe("Winter map");
  });

  it("fills the remaining slots from other channels once the channel runs out", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-same", title: "Same channel", published_at: "2026-10-14T09:00:00Z" }),
        sibling({ id: "a-other", title: "Other channel", channel: PRODUCT }),
      ],
    });

    expect(result?.lead.title).toBe("Same channel");
    expect(result?.rest.map((c) => c.title)).toEqual(["Other channel"]);
  });

  it("shows at most three cards beside the lead", () => {
    const result = build({
      siblings: Array.from({ length: 9 }, (_, i) =>
        sibling({ id: `a-${i}`, slug: `a-${i}`, published_at: `2026-0${i + 1}-01T09:00:00Z` }),
      ),
    });

    expect(result?.rest).toHaveLength(3);
  });

  it("never offers the article the reader is already on", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-current", title: "This one" }),
        sibling({ id: "a-other", title: "Another" }),
      ],
    });

    expect(result?.lead.title).toBe("Another");
    expect(result?.rest).toHaveLength(0);
  });

  it("leaves out drafts and anything without a slug", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-draft", title: "Draft", state: "draft" }),
        sibling({ id: "a-slugless", title: "Slugless", slug: null }),
        sibling({ id: "a-live", title: "Live" }),
      ],
    });

    expect(result?.lead.title).toBe("Live");
    expect(result?.rest).toHaveLength(0);
  });

  it("falls through to the site feed when the project has published nothing else", () => {
    const result = build({ siblings: [], feed: [feedEntry()] });

    expect(result?.heading).toBe("Elsewhere on Naglasúpan");
    expect(result?.lead.title).toBe("Counting cyclists with a doorbell camera");
    expect(result?.lead.href).toBe("/projects/reykjavik-bikes/articles/counting-cyclists");
    expect(result?.moreHref).toBe("/latest");
  });

  it("labels a feed card with its project, not its channel", () => {
    const result = build({ siblings: [], feed: [feedEntry()] });

    expect(result?.lead.flag).toBe("Reykjavik Bikes");
  });

  it("ignores feed entries that carry no article", () => {
    const result = build({
      siblings: [],
      feed: [feedEntry({ article: null, kind: "project_published" }), feedEntry()],
    });

    expect(result?.lead.title).toBe("Counting cyclists with a doorbell camera");
    expect(result?.rest).toHaveLength(0);
  });

  it("renders nothing when there is nothing at all to go on to", () => {
    expect(build({ siblings: [], feed: [] })).toBeNull();
    expect(build({ siblings: null, feed: null })).toBeNull();
  });

  it("links through the project slug, falling back to its id", () => {
    const bySlug = build({ siblings: [sibling()] });
    const byId = build({ project: project({ slug: null }), siblings: [sibling()] });

    expect(bySlug?.lead.href).toBe("/projects/hot-spring-finder/articles/offline-tiles");
    expect(byId?.lead.href).toBe("/projects/p-1/articles/offline-tiles");
  });

  it("counts the current article in the link to all of them", () => {
    const result = build({
      siblings: [sibling({ id: "a-1", slug: "a-1" }), sibling({ id: "a-2", slug: "a-2" })],
    });

    expect(result?.moreLabel).toBe("All 3 articles from Hot Spring Finder");
    expect(result?.moreHref).toBe("/projects/hot-spring-finder#articles");
  });
});
