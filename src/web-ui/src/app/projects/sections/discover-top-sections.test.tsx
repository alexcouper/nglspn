import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { CompetitionSummary, FrontPageArticle } from "@/lib/api";
import type { CompetitionSlot } from "@/lib/discover-top";
import { RecentSection } from "./RecentSection";
import { SpotlightSection } from "./SpotlightSection";

// ------------------------------------------------------------------ mounting

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

// --------------------------------------------------------------- factories

function projectArticle(id: string, overrides: Partial<FrontPageArticle> = {}): FrontPageArticle {
  return {
    id,
    slug: `article-${id}`,
    title: `Article ${id}`,
    summary: `Summary of ${id}`,
    published_at: "2026-11-20T10:00:00Z",
    channel_name: "Reviews",
    project_slug: "naglasupan",
    project_title: "Naglasúpan",
    author_id: "author-1",
    author_name: "Anna Jónsdóttir",
    author_avatar_url: null,
    listing_image_url: "https://cdn.example/listing.png",
    listing_crop: null,
    ...overrides,
  };
}

function authorArticle(id: string, overrides: Partial<FrontPageArticle> = {}): FrontPageArticle {
  return projectArticle(id, {
    channel_name: "Una's channel",
    project_slug: null,
    project_title: null,
    author_id: "user-u",
    author_name: "Una Úlfsdóttir",
    ...overrides,
  });
}

function slot(): CompetitionSlot {
  const competition: CompetitionSummary = {
    name: "Grasker",
    slug: "grasker",
    submission_deadline: "2026-11-20",
    voting_end_date: "2026-12-02",
    prize_amount: null,
    status: "voting",
    image_url: null,
    project_count: 4,
    winner: null,
  };
  return { state: "voting", competition, daysLeft: 6 };
}

// --------------------------------------------------------------- assertions

function piece(container: HTMLElement, name: "lead" | "second" | "slot"): HTMLElement | null {
  const testId = name === "slot" ? "competition-slot" : `recent-${name}`;
  return container.querySelector(`[data-testid="${testId}"]`);
}

// The stacked order is set with CSS `order`, so read it off the classes that
// apply below the `md` breakpoint.
function stackedOrder(container: HTMLElement): string[] {
  const names = ["lead", "second", "slot"] as const;
  return names
    .map((name) => ({ name, element: piece(container, name) }))
    .filter((p): p is { name: (typeof names)[number]; element: HTMLElement } => !!p.element)
    .sort((a, b) => mobileOrder(a.element) - mobileOrder(b.element))
    .map((p) => p.name);
}

function mobileOrder(element: HTMLElement): number {
  const match = element.className.match(/(?:^|\s)order-(\d+)/);
  return match ? Number(match[1]) : 0;
}

function linkOf(element: HTMLElement | null): string | null | undefined {
  return element?.querySelector("a")?.getAttribute("href");
}

function isOverlayCard(element: HTMLElement | null): boolean {
  return !!element?.querySelector('[data-testid="article-card-overlay"]');
}

// ---------------------------------------------------------------- the tests

describe("RecentSection", () => {
  it("puts the newest article first, the second beside it and the slot below that", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={projectArticle("a")} second={projectArticle("b")} slot={slot()} />,
    );

    expect(piece(container, "lead")?.textContent).toContain("Article a");
    expect(piece(container, "lead")?.className).toContain("md:row-span-2");
    expect(isOverlayCard(piece(container, "second"))).toBe(true);
    expect(piece(container, "second")?.className).toContain("md:order-2");
    expect(piece(container, "slot")?.className).toContain("md:order-3");

    unmount();
  });

  it("stacks the slot between the lead and the second article on narrow screens", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={projectArticle("a")} second={projectArticle("b")} slot={slot()} />,
    );

    expect(stackedOrder(container)).toEqual(["lead", "slot", "second"]);

    unmount();
  });

  it("lets the second article fill the right column when there is no slot", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={projectArticle("a")} second={projectArticle("b")} slot={null} />,
    );

    expect(piece(container, "slot")).toBeNull();
    expect(isOverlayCard(piece(container, "second"))).toBe(false);
    expect(piece(container, "second")?.textContent).toContain("Summary of b");
    expect(piece(container, "lead")?.className).not.toContain("md:row-span-2");

    unmount();
  });

  it("gives the right column to the slot alone when there is one article", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={projectArticle("a")} second={null} slot={slot()} />,
    );

    expect(piece(container, "second")).toBeNull();
    expect(stackedOrder(container)).toEqual(["lead", "slot"]);

    unmount();
  });

  it("renders nothing without articles, even with a competition to show", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={null} second={null} slot={slot()} />,
    );

    expect(container.innerHTML).toBe("");

    unmount();
  });

  it("links project articles under the project, marked as opened from Discover", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={projectArticle("a")} second={null} slot={null} />,
    );

    expect(linkOf(piece(container, "lead"))).toBe(
      "/projects/naglasupan/articles/article-a?from=discover",
    );
    expect(piece(container, "lead")?.textContent).toContain("Naglasúpan");
    expect(piece(container, "lead")?.textContent).toContain("Reviews");

    unmount();
  });

  it("flags an author-owned article with its author and links it under them", async () => {
    const { container, unmount } = await mount(
      <RecentSection lead={authorArticle("a")} second={null} slot={null} />,
    );

    expect(linkOf(piece(container, "lead"))).toBe(
      "/users/user-u/articles/article-a?from=discover",
    );
    expect(piece(container, "lead")?.textContent).toContain("Una Úlfsdóttir");
    expect(piece(container, "lead")?.textContent).not.toContain("Una's channel");

    unmount();
  });

  it("draws a text-led card with no image for an article without one", async () => {
    const { container, unmount } = await mount(
      <RecentSection
        lead={projectArticle("a", { listing_image_url: null })}
        second={null}
        slot={null}
      />,
    );

    expect(piece(container, "lead")?.querySelector("img")).toBeNull();
    expect(piece(container, "lead")?.textContent).toContain("Summary of a");

    unmount();
  });
});

describe("SpotlightSection", () => {
  it("shows a heading and a grid card per spotlighted article", async () => {
    const { container, unmount } = await mount(
      <SpotlightSection articles={[projectArticle("c"), projectArticle("d")]} />,
    );

    expect(container.querySelector("h2")?.textContent).toBe("In the spotlight");
    const cards = container.querySelectorAll('[data-testid="spotlight-cards"] article');
    expect(cards).toHaveLength(2);
    expect(linkOf(cards[0] as HTMLElement)).toBe(
      "/projects/naglasupan/articles/article-c?from=discover",
    );

    unmount();
  });

  it("renders nothing when no spotlighted articles are left", async () => {
    const { container, unmount } = await mount(<SpotlightSection articles={[]} />);

    expect(container.innerHTML).toBe("");

    unmount();
  });
});
