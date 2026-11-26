import { describe, expect, it } from "vitest";

import type {
  Article,
  ArticleListItem,
  FrontPageArticle,
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

function recentArticle(overrides: Partial<FrontPageArticle> = {}): FrontPageArticle {
  return {
    id: "a-elsewhere",
    slug: "counting-cyclists",
    title: "Counting cyclists with a doorbell camera",
    summary: "A €30 camera and four weekends.",
    published_at: "2026-10-01T09:00:00Z",
    channel_name: "Updates",
    project_slug: "reykjavik-bikes",
    project_title: "Reykjavik Bikes",
    author_id: null,
    author_name: null,
    author_avatar_url: null,
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  };
}

function build(overrides: Parameters<typeof buildOnward>[0] | object = {}) {
  return buildOnward({
    container: projectContainer(project()),
    article: article(),
    siblings: [],
    recent: null,
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

function recentArticles(count: number): FrontPageArticle[] {
  return Array.from({ length: count }, (_, i) =>
    recentArticle({ id: `a-recent-${i}`, slug: `recent-${i}`, title: `Recent ${i}` }),
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
    const result = build({ siblings: projectArticles(9), recent: recentArticles(3) });

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

  it("falls through to recent articles when the project has published nothing else", () => {
    const result = build({ siblings: [], recent: [recentArticle()] });

    expect(result?.primary.heading).toEqual({ kind: "elsewhere" });
    expect(leadTitle(result)).toBe("Counting cyclists with a doorbell camera");
    expect(result?.primary.cards[0].href).toBe("/projects/reykjavik-bikes/articles/counting-cyclists");
    expect(result?.topUp).toBeNull();
    expect(result?.more).toEqual({ kind: "discover", href: "/projects" });
  });

  it("tops up a thin project from recent articles under its own heading", () => {
    const result = build({ siblings: projectArticles(1), recent: recentArticles(5) });

    expect(result?.primary.heading).toEqual({ kind: "channel", channel: "Updates" });
    expect(leadTitle(result)).toBe("Article 0");
    expect(result?.topUp?.heading).toEqual({ kind: "elsewhere" });
    expect(topUpTitles(result)).toEqual(["Recent 0", "Recent 1", "Recent 2"]);
  });

  it("only tops up the slots the project leaves empty", () => {
    const result = build({ siblings: projectArticles(2), recent: recentArticles(5) });

    expect(restTitles(result)).toEqual(["Article 0"]);
    expect(topUpTitles(result)).toEqual(["Recent 0", "Recent 1"]);
  });

  it("keeps the project link when recent articles top it up", () => {
    const result = build({ siblings: projectArticles(1), recent: recentArticles(3) });

    expect(result?.more).toMatchObject({ kind: "project", count: 2 });
  });

  it("does not top up with this project's own recent articles", () => {
    const ownArticle = recentArticle({ id: "a-own", project_slug: "hot-spring-finder", title: "Own" });
    const result = build({ siblings: projectArticles(1), recent: [ownArticle, ...recentArticles(1)] });

    expect(topUpTitles(result)).toEqual(["Recent 0"]);
  });

  it("does not repeat an article that appears twice in recent", () => {
    const [entry] = recentArticles(1);
    const result = build({ siblings: projectArticles(1), recent: [entry, entry] });

    expect(topUpTitles(result)).toEqual(["Recent 0"]);
  });

  it("labels a recent card with its project, not its channel", () => {
    const result = build({ siblings: [], recent: [recentArticle()] });

    expect(result?.primary.cards[0].flag).toBe("Reykjavik Bikes");
  });

  it("skips a recent article that has no slug to link to", () => {
    const result = build({
      siblings: [],
      recent: [recentArticle({ id: "a-slugless", slug: null, title: "Slugless" }), recentArticle()],
    });

    expect(leadTitle(result)).toBe("Counting cyclists with a doorbell camera");
    expect(restTitles(result)).toEqual([]);
  });

  it("renders nothing when there is nothing at all to go on to", () => {
    expect(build({ siblings: [], recent: [] })).toBeNull();
    expect(build({ siblings: null, recent: null })).toBeNull();
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
      recent: null,
    });

    expect(result).toBeNull();
  });

  it("does not top up with the author's own recent articles", () => {
    const own = recentArticle({
      id: "a-own-recent",
      project_slug: null,
      project_title: null,
      author_id: "u-1",
      title: "Own in recent",
    });
    const result = buildForAuthor({ siblings: [], recent: [own, ...recentArticles(1)] });

    expect(leadTitle(result)).toBe("Recent 0");
  });

  it("links a recent card for someone else's author-owned article under their profile", () => {
    const theirs = recentArticle({
      id: "a-theirs",
      slug: "theirs",
      title: "Theirs",
      project_slug: null,
      project_title: null,
      author_id: "u-2",
      author_name: "Bjarki",
    });
    const result = build({ siblings: [], recent: [theirs] });

    expect(result?.primary.cards[0].href).toBe("/users/u-2/articles/theirs");
    expect(result?.primary.cards[0].flag).toBe("Bjarki");
  });
});
