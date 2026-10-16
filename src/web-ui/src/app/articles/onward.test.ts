import { describe, expect, it } from "vitest";

import type {
  Article,
  ArticleListItem,
  FeedEntry,
  Project,
  PublicUserProfile,
  UserArticle,
} from "@/lib/api";

import { authorContainer, projectContainer } from "./container";
import { buildOnward, ONWARD_SLOTS, type Onward } from "./onward";

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
      author_id: null,
      author_name: null,
      author_avatar_url: null,
      listing_image_url: null,
      listing_crop: null,
    },
    ...overrides,
  } as FeedEntry;
}

function build(overrides: Parameters<typeof buildOnward>[0] | object = {}) {
  return buildOnward({
    container: projectContainer(project()),
    article: article(),
    siblings: [],
    feed: null,
    ...overrides,
  } as Parameters<typeof buildOnward>[0]);
}

const AUTHOR = {
  id: "u-1",
  first_name: "Sigrún",
  last_name: "Haraldsdóttir",
} as PublicUserProfile;

function ownArticle(overrides: Partial<UserArticle> = {}): UserArticle {
  return {
    id: "a-own-other",
    title: "On keeping a notebook",
    summary: "",
    slug: "notebook",
    published_at: "2026-10-14T09:00:00Z",
    channel: { id: "ch-personal", name: "Articles" },
    project: null,
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  } as UserArticle;
}

function buildForAuthor(overrides: object = {}) {
  return build({
    container: authorContainer(AUTHOR),
    article: article({ id: "a-current", project: null, channel: { id: "ch-personal", name: "Articles" } }),
    ...overrides,
  });
}

function leadTitle(result: Onward | null): string | undefined {
  return result?.primary.cards[0]?.title;
}

function restTitles(result: Onward | null): string[] {
  return result?.primary.cards.slice(1).map((c) => c.title) ?? [];
}

function topUpTitles(result: Onward | null): string[] {
  return result?.topUp?.cards.map((c) => c.title) ?? [];
}

function projectArticles(count: number): ArticleListItem[] {
  return Array.from({ length: count }, (_, i) =>
    sibling({ id: `a-${i}`, slug: `a-${i}`, title: `Article ${i}`, published_at: `2026-0${i + 1}-01T09:00:00Z` }),
  );
}

function feedArticles(count: number): FeedEntry[] {
  return Array.from({ length: count }, (_, i) =>
    feedEntry({
      id: `f-${i}`,
      article: { ...feedEntry().article!, id: `a-feed-${i}`, slug: `feed-${i}`, title: `Feed ${i}` },
    }),
  );
}

describe("buildOnward", () => {
  it("leads with the nearest article in the same channel", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-newer", title: "Newer", published_at: "2026-10-14T09:00:00Z" }),
        sibling({ id: "a-older", title: "Older", published_at: "2026-09-01T09:00:00Z" }),
      ],
    });

    expect(result?.primary.heading).toEqual({ kind: "channel", channel: "Updates" });
    expect(leadTitle(result)).toBe("Newer");
  });

  it("keeps the channel heading when this is the newest in the channel", () => {
    const result = build({
      siblings: [sibling({ id: "a-older", title: "Older", published_at: "2026-09-01T09:00:00Z" })],
    });

    expect(result?.primary.heading).toEqual({ kind: "channel", channel: "Updates" });
    expect(leadTitle(result)).toBe("Older");
  });

  it("names the project instead when the channel has nothing else", () => {
    const result = build({
      siblings: [sibling({ id: "a-other-channel", title: "Winter map", channel: PRODUCT })],
    });

    expect(result?.primary.heading).toEqual({ kind: "project", project: "Hot Spring Finder" });
    expect(leadTitle(result)).toBe("Winter map");
  });

  it("names the project once other channels fill in after the channel runs out", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-same", title: "Same channel", published_at: "2026-10-14T09:00:00Z" }),
        sibling({ id: "a-other", title: "Other channel", channel: PRODUCT }),
      ],
    });

    expect(result?.primary.heading).toEqual({ kind: "project", project: "Hot Spring Finder" });
    expect(leadTitle(result)).toBe("Same channel");
    expect(restTitles(result)).toEqual(["Other channel"]);
  });

  it("keeps the channel heading when other channels are pushed out by the slot limit", () => {
    const result = build({
      siblings: [
        ...projectArticles(ONWARD_SLOTS),
        sibling({ id: "a-other", title: "Other channel", channel: PRODUCT, published_at: "2025-01-01T09:00:00Z" }),
      ],
    });

    expect(result?.primary.heading).toEqual({ kind: "channel", channel: "Updates" });
    expect(restTitles(result)).not.toContain("Other channel");
  });

  it("shows at most three cards beside the lead", () => {
    const result = build({ siblings: projectArticles(9), feed: feedArticles(3) });

    expect(restTitles(result)).toHaveLength(3);
    expect(result?.topUp).toBeNull();
  });

  it("never offers the article the reader is already on", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-current", title: "This one" }),
        sibling({ id: "a-other", title: "Another" }),
      ],
    });

    expect(leadTitle(result)).toBe("Another");
    expect(restTitles(result)).toEqual([]);
  });

  it("leaves out drafts and anything without a slug", () => {
    const result = build({
      siblings: [
        sibling({ id: "a-draft", title: "Draft", state: "draft" }),
        sibling({ id: "a-slugless", title: "Slugless", slug: null }),
        sibling({ id: "a-live", title: "Live" }),
      ],
    });

    expect(leadTitle(result)).toBe("Live");
    expect(restTitles(result)).toEqual([]);
  });

  it("falls through to the site feed when the project has published nothing else", () => {
    const result = build({ siblings: [], feed: [feedEntry()] });

    expect(result?.primary.heading).toEqual({ kind: "elsewhere" });
    expect(leadTitle(result)).toBe("Counting cyclists with a doorbell camera");
    expect(result?.primary.cards[0].href).toBe("/projects/reykjavik-bikes/articles/counting-cyclists");
    expect(result?.topUp).toBeNull();
    expect(result?.more).toEqual({ kind: "latest", href: "/latest" });
  });

  it("tops up a thin project from the feed under its own heading", () => {
    const result = build({ siblings: projectArticles(1), feed: feedArticles(5) });

    expect(result?.primary.heading).toEqual({ kind: "channel", channel: "Updates" });
    expect(leadTitle(result)).toBe("Article 0");
    expect(result?.topUp?.heading).toEqual({ kind: "elsewhere" });
    expect(topUpTitles(result)).toEqual(["Feed 0", "Feed 1", "Feed 2"]);
  });

  it("only tops up the slots the project leaves empty", () => {
    const result = build({ siblings: projectArticles(2), feed: feedArticles(5) });

    expect(restTitles(result)).toEqual(["Article 0"]);
    expect(topUpTitles(result)).toEqual(["Feed 0", "Feed 1"]);
  });

  it("keeps the project link when the feed tops it up", () => {
    const result = build({ siblings: projectArticles(1), feed: feedArticles(3) });

    expect(result?.more).toMatchObject({ kind: "project", count: 2 });
  });

  it("does not top up with this project's own articles from the feed", () => {
    const ownArticle = feedEntry({
      id: "f-own",
      article: { ...feedEntry().article!, id: "a-own", project_slug: "hot-spring-finder", title: "Own" },
    });
    const result = build({ siblings: projectArticles(1), feed: [ownArticle, ...feedArticles(1)] });

    expect(topUpTitles(result)).toEqual(["Feed 0"]);
  });

  it("does not repeat an article that appears twice in the feed", () => {
    const [entry] = feedArticles(1);
    const result = build({ siblings: projectArticles(1), feed: [entry, { ...entry, id: "f-again" }] });

    expect(topUpTitles(result)).toEqual(["Feed 0"]);
  });

  it("labels a feed card with its project, not its channel", () => {
    const result = build({ siblings: [], feed: [feedEntry()] });

    expect(result?.primary.cards[0].flag).toBe("Reykjavik Bikes");
  });

  it("ignores feed entries that carry no article", () => {
    const result = build({
      siblings: [],
      feed: [feedEntry({ article: null, kind: "project_published" }), feedEntry()],
    });

    expect(leadTitle(result)).toBe("Counting cyclists with a doorbell camera");
    expect(restTitles(result)).toEqual([]);
  });

  it("renders nothing when there is nothing at all to go on to", () => {
    expect(build({ siblings: [], feed: [] })).toBeNull();
    expect(build({ siblings: null, feed: null })).toBeNull();
  });

  it("links through the project slug, falling back to its id", () => {
    const bySlug = build({ siblings: [sibling()] });
    const byId = build({
      container: projectContainer(project({ slug: null })),
      siblings: [sibling()],
    });

    expect(bySlug?.primary.cards[0].href).toBe("/projects/hot-spring-finder/articles/offline-tiles");
    expect(byId?.primary.cards[0].href).toBe("/projects/p-1/articles/offline-tiles");
  });

  it("counts the current article in the link to all of them", () => {
    const result = build({
      siblings: [sibling({ id: "a-1", slug: "a-1" }), sibling({ id: "a-2", slug: "a-2" })],
    });

    expect(result?.more).toEqual({
      kind: "project",
      href: "/projects/hot-spring-finder#articles",
      count: 3,
      project: "Hot Spring Finder",
    });
  });
});


describe("buildOnward for an author-owned article", () => {
  it("heads the author's other articles with their name and links under their profile", () => {
    const result = buildForAuthor({ siblings: [ownArticle()] });

    expect(result?.primary.heading).toEqual({ kind: "author", author: "Sigrún Haraldsdóttir" });
    expect(result?.primary.cards[0].href).toBe("/users/u-1/articles/notebook");
    expect(result?.primary.cards[0].flag).toBe("Sigrún Haraldsdóttir");
    expect(result?.more).toEqual({
      kind: "author",
      href: "/users/u-1#profile-articles",
      count: 2,
      author: "Sigrún Haraldsdóttir",
    });
  });

  it("leaves the author's project articles to their projects", () => {
    const result = buildForAuthor({
      siblings: [
        ownArticle({ id: "a-on-project", title: "On a project", project: { id: "p", slug: "p", title: "P" } }),
      ],
      feed: null,
    });

    expect(result).toBeNull();
  });

  it("does not top up with the author's own feed entries", () => {
    const own = feedEntry({
      id: "f-own",
      article: { ...feedEntry().article!, id: "a-own-feed", project_slug: null, project_title: null, author_id: "u-1", title: "Own in feed" },
    });
    const result = buildForAuthor({ siblings: [], feed: [own, ...feedArticles(1)] });

    expect(leadTitle(result)).toBe("Feed 0");
  });

  it("links a feed card for someone else's author-owned article under their profile", () => {
    const theirs = feedEntry({
      article: {
        ...feedEntry().article!,
        id: "a-theirs",
        slug: "theirs",
        title: "Theirs",
        project_slug: null,
        project_title: null,
        author_id: "u-2",
        author_name: "Bjarki",
      },
    });
    const result = build({ siblings: [], feed: [theirs] });

    expect(result?.primary.cards[0].href).toBe("/users/u-2/articles/theirs");
    expect(result?.primary.cards[0].flag).toBe("Bjarki");
  });
});
