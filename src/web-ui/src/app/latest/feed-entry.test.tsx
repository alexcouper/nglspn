import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { FeedEntry } from "@/lib/api";

import { FeedRow } from "./FeedRow";
import { groupByWeek, renderEntry, weekLabel } from "./feedEntry";

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

function entry(overrides: Partial<FeedEntry> = {}): FeedEntry {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    kind: "project_published",
    occurred_at: "2026-08-10T09:00:00Z",
    is_pinned: false,
    project: null,
    competition: null,
    article: null,
    discussion: null,
    supersedes: null,
    ...overrides,
  } as FeedEntry;
}

function projectRef(overrides = {}) {
  return {
    id: "00000000-0000-0000-0000-0000000000a1",
    slug: "hverfid",
    title: "Hverfið",
    tagline: "Borrow a drill instead of buying one",
    category_name: "Community & Public Good",
    icon_url: "https://example.test/icon.png",
    ...overrides,
  };
}

function articleRef(overrides = {}) {
  return {
    id: "00000000-0000-0000-0000-0000000000b1",
    slug: "how-broadside-won",
    title: "How Broadside won Chili",
    summary: "A tactical naval battler built in eight weeks.",
    channel_name: "Competition Winners",
    project_slug: "naglasupan",
    project_title: "Naglasúpan",
    listing_image_url: "https://example.test/lead.jpg",
    listing_crop: null,
    ...overrides,
  };
}

function competitionRef(overrides = {}) {
  return {
    id: "00000000-0000-0000-0000-0000000000c1",
    slug: "chili",
    name: "Chili",
    winner_slug: "broadside",
    ...overrides,
  };
}

describe("renderEntry", () => {
  it("labels a bare project event as a new project", () => {
    const rendered = renderEntry(
      entry({ kind: "project_published", project: projectRef() }),
    );

    expect(rendered.flag).toBe("New project");
    expect(rendered.headline).toBe("Hverfið");
    expect(rendered.href).toBe("/projects/hverfid");
    expect(rendered.hasArticle).toBe(false);
  });

  it("distinguishes a tipoff from a new project", () => {
    const rendered = renderEntry(
      entry({ kind: "project_tipoff", project: projectRef() }),
    );

    expect(rendered.flag).toBe("Tipoff");
  });

  it("labels a standalone article with the project it came from", () => {
    const rendered = renderEntry(
      entry({
        kind: "article_published",
        article: articleRef({ channel_name: "Updates" }),
      }),
    );

    expect(rendered.flag).toBe("Naglasúpan");
    expect(rendered.hasArticle).toBe(true);
  });

  it("does not repeat the project in the meta line below it", () => {
    const rendered = renderEntry(
      entry({
        kind: "article_published",
        article: articleRef({ channel_name: "Updates" }),
      }),
    );

    expect(rendered.meta).toBe("Updates");
  });

  it("keeps the project in the meta line when the event holds the flag", () => {
    const rendered = renderEntry(
      entry({
        kind: "article_published",
        article: articleRef({ channel_name: "Updates" }),
        supersedes: {
          kind: "competition_winner",
          competition: competitionRef(),
          project: null,
        },
      }),
    );

    expect(rendered.flag).toBe("Competition winner");
    expect(rendered.meta).toBe("Naglasúpan · Updates");
  });

  it("keeps the superseded event's flag on a write-up", () => {
    const rendered = renderEntry(
      entry({
        kind: "article_published",
        article: articleRef(),
        supersedes: {
          kind: "competition_winner",
          competition: competitionRef(),
          project: null,
        },
      }),
    );

    expect(rendered.flag).toBe("Competition winner");
    expect(rendered.headline).toBe("How Broadside won Chili");
    expect(rendered.href).toBe(
      "/projects/naglasupan/articles/how-broadside-won",
    );
  });

  it("links a bare competition event by slug, as the rest of the site does", () => {
    const rendered = renderEntry(
      entry({ kind: "competition_winner", competition: competitionRef() }),
    );

    expect(rendered.flag).toBe("Competition winner");
    expect(rendered.headline).toBe("Chili has a winner");
    expect(rendered.href).toBe("/competitions/chili");
  });

  it("has no link when an article has no slug yet", () => {
    const rendered = renderEntry(
      entry({ kind: "article_published", article: articleRef({ slug: null }) }),
    );

    expect(rendered.href).toBeNull();
  });
});

describe("groupByWeek", () => {
  it("keeps entries in order and does not reorder across groups", () => {
    const groups = groupByWeek([
      entry({ id: "a", occurred_at: "2026-08-12T09:00:00Z" }),
      entry({ id: "b", occurred_at: "2026-08-11T09:00:00Z" }),
      entry({ id: "c", occurred_at: "2026-08-04T09:00:00Z" }),
    ]);

    expect(groups.map((g) => g.entries.map((e) => e.id))).toEqual([
      ["a", "b"],
      ["c"],
    ]);
  });

  it("labels the current and previous weeks in words", () => {
    const now = new Date("2026-08-13T12:00:00Z");

    expect(weekLabel(new Date("2026-08-10T00:00:00"), now)).toBe("This week");
    expect(weekLabel(new Date("2026-08-03T00:00:00"), now)).toBe("Last week");
  });
});

describe("FeedRow", () => {
  it("renders an image for an article that has one", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({ kind: "article_published", article: articleRef() })}
        variant="lead"
      />,
    );

    expect(
      container.querySelector('[data-testid="article-listing-image"]'),
    ).not.toBeNull();
    cleanup();
  });

  it("renders no placeholder when an article has no image", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({
          kind: "article_published",
          article: articleRef({ listing_image_url: null }),
        })}
        variant="row"
      />,
    );

    expect(
      container.querySelector('[data-testid="article-listing-image"]'),
    ).toBeNull();
    expect(container.textContent).toContain("How Broadside won Chili");
    cleanup();
  });

  it("renders the project icon on a new-project row", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({ kind: "project_published", project: projectRef() })}
        variant="row"
      />,
    );

    const img = container.querySelector("img");
    expect(img?.getAttribute("src")).toBe("https://example.test/icon.png");
    cleanup();
  });

  it("renders no image for a project that has none", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({
          kind: "project_published",
          project: projectRef({ icon_url: null }),
        })}
        variant="row"
      />,
    );

    expect(container.querySelector("img")).toBeNull();
    cleanup();
  });

  it("renders a bare event without a summary", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({ kind: "project_published", project: projectRef() })}
        variant="row"
      />,
    );

    expect(container.textContent).toContain("New project");
    expect(container.textContent).not.toContain(
      "Borrow a drill instead of buying one",
    );
    cleanup();
  });

  it("gives the lead the full-width treatment", async () => {
    const { container, unmount: cleanup } = await mount(
      <FeedRow
        entry={entry({ kind: "article_published", article: articleRef() })}
        variant="lead"
      />,
    );

    expect(
      container.querySelector('[data-testid="feed-entry-lead"]'),
    ).not.toBeNull();
    cleanup();
  });
});
