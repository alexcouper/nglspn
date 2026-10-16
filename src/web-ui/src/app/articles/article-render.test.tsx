import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Article, Project, PublicUserProfile } from "@/lib/api";

import { ArticleRenderContent } from "./ArticleRenderContent";
import { authorContainer, projectContainer } from "./container";
import type { Onward, OnwardCard } from "./onward";

vi.mock("@/contexts/auth", () => ({
  useAuth: () => ({ isAuthenticated: false, isLoading: false }),
}));
// The onward footer's Follow button reads the router for its login redirect.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
}));
vi.mock("@/contexts/notifications", () => ({
  useNotifications: () => ({ markArticleRead: vi.fn().mockResolvedValue(undefined) }),
}));

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "p-1",
    slug: "hot-spring-finder",
    title: "Hot Spring Finder",
    images: [],
    ...overrides,
  } as Project;
}

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "a-1",
    title: "We mapped 94 unmarked hot springs",
    body: "The first version had 212 pins on it.",
    summary: "Six months of GPS traces.",
    summary_display: "Six months of GPS traces.",
    slug: "we-mapped-94",
    state: "published",
    published_at: "2026-10-02T09:00:00Z",
    channel: { id: "ch-1", name: "Updates" },
    author: {
      id: "u-1",
      first_name: "Sigrún",
      last_name: "Haraldsdóttir",
      is_system_user: false,
    },
    listing_image_url: null,
    listing_crop: null,
    ...overrides,
  } as Article;
}

function card(overrides: Partial<OnwardCard> = {}): OnwardCard {
  return {
    id: "a-card",
    href: "/projects/hot-spring-finder/articles/card",
    flag: "Updates",
    title: "A card",
    summary: "",
    imageUrl: null,
    crop: null,
    ...overrides,
  };
}

function onward(overrides: Partial<Onward> = {}): Onward {
  return {
    primary: {
      heading: { kind: "channel", channel: "Updates" },
      cards: [card({ id: "a-2", title: "Offline tiles", href: "/projects/hot-spring-finder/articles/offline-tiles" })],
    },
    topUp: null,
    more: {
      kind: "project",
      href: "/projects/hot-spring-finder#articles",
      count: 4,
      project: "Hot Spring Finder",
    },
    ...overrides,
  };
}

async function render(props: Partial<Parameters<typeof ArticleRenderContent>[0]> = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  let root!: Root;
  await act(async () => {
    root = createRoot(container);
    root.render(
      <ArticleRenderContent
        container={projectContainer(project())}
        article={article()}
        origin={{ kind: "latest", href: "/latest" }}
        onward={null}
        articleCount={4}
        channelCount={2}
        {...props}
      />,
    );
  });
  return {
    container,
    cleanup: () => {
      act(() => root.unmount());
      container.remove();
    },
  };
}

function headings(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("section h2")).map((h) => h.textContent ?? "");
}

function backLink(container: HTMLElement): HTMLAnchorElement | null {
  return container.querySelector('a[href="/latest"], a[href^="/projects/"][href$="#articles"]');
}

describe("ArticleRenderContent", () => {
  it("names the place the reader came from on the back control", async () => {
    const { container, cleanup } = await render();

    expect(backLink(container)?.textContent).toContain("Latest");
    expect(backLink(container)?.getAttribute("href")).toBe("/latest");
    cleanup();
  });

  it("falls back to the project when the reader arrived directly", async () => {
    const { container, cleanup } = await render({
      origin: {
        kind: "container",
        href: "/projects/hot-spring-finder#articles",
        title: "Hot Spring Finder",
      },
    });

    expect(backLink(container)?.textContent).toContain("Hot Spring Finder");
    cleanup();
  });

  it("shows the listing image as a band when the article has one", async () => {
    const { container, cleanup } = await render({
      article: article({ listing_image_url: "https://example.test/lead.jpg" }),
    });

    expect(
      container.querySelector('[data-testid="article-listing-image"]'),
    ).not.toBeNull();
    cleanup();
  });

  it("draws no band and no placeholder when the article has no image", async () => {
    const { container, cleanup } = await render();

    expect(
      container.querySelector('[data-testid="article-listing-image"]'),
    ).toBeNull();
    expect(container.querySelector("figure")).toBeNull();
    cleanup();
  });

  it("estimates the reading time from the body", async () => {
    const { container, cleanup } = await render({
      article: article({ body: "word ".repeat(600) }),
    });

    expect(container.textContent).toContain("3 min read");
    cleanup();
  });

  it("hands the reader onward when there is something to go to", async () => {
    const { container, cleanup } = await render({ onward: onward() });

    expect(container.textContent).toContain("More in Updates");
    expect(
      container.querySelector('a[href="/projects/hot-spring-finder/articles/offline-tiles"]'),
    ).not.toBeNull();
    cleanup();
  });

  it("labels feed cards that top up a thin project separately", async () => {
    const { container, cleanup } = await render({
      onward: onward({
        topUp: {
          heading: { kind: "elsewhere" },
          cards: [card({ id: "a-feed", title: "Counting cyclists", flag: "Reykjavik Bikes" })],
        },
      }),
    });

    expect(headings(container)).toEqual(["More in Updates", "Elsewhere on Naglasúpan"]);
    expect(container.textContent).toContain("Counting cyclists");
    cleanup();
  });

  it("puts the article and the onward section in separate landmarks", async () => {
    const { container, cleanup } = await render({ onward: onward() });

    expect(container.querySelectorAll("main")).toHaveLength(0);
    expect(container.querySelector("article h1")).not.toBeNull();
    expect(container.querySelector("article section")).toBeNull();
    cleanup();
  });

  it("ends at the body when there is nothing to go on to", async () => {
    const { container, cleanup } = await render({ onward: null });

    expect(container.textContent).not.toContain("More in");
    expect(container.querySelector("section")).toBeNull();
    cleanup();
  });

  it("marks a draft as one", async () => {
    const { container, cleanup } = await render({
      article: article({ state: "draft" }),
    });

    expect(container.textContent).toContain("Draft");
    cleanup();
  });

  it("credits the author but never the system user", async () => {
    const byPerson = await render();
    expect(byPerson.container.textContent).toContain("Sigrún Haraldsdóttir");
    byPerson.cleanup();

    const bySystem = await render({
      article: article({
        author: {
          id: "u-sys",
          first_name: "Nagla",
          last_name: "Súpan",
          is_system_user: true,
        },
      } as Partial<Article>),
    });
    expect(bySystem.container.textContent).not.toContain("Nagla Súpan");
    bySystem.cleanup();
  });

  it("renders the project and channel above the title", async () => {
    const { container, cleanup } = await render();

    const heading = container.querySelector("h1");
    expect(heading?.textContent).toBe("We mapped 94 unmarked hot springs");
    expect(container.textContent).toContain("Hot Spring Finder");
    expect(container.textContent).toContain("Updates");
    cleanup();
  });
});


describe("ArticleRenderContent for an author-owned article", () => {
  const author = {
    id: "u-1",
    first_name: "Sigrún",
    last_name: "Haraldsdóttir",
    is_system_user: false,
    avatar_url: null,
  } as PublicUserProfile;

  it("shows the author where the project would be, and no channel", async () => {
    const { container, cleanup } = await render({
      container: authorContainer(author),
      article: article({ project: null, channel: { id: "ch-personal", name: "Articles" } }),
    });

    const head = container.querySelector('[data-testid="article-container"]');
    expect(head?.getAttribute("href")).toBe("/users/u-1");
    expect(head?.textContent).toContain("Sigrún Haraldsdóttir");
    expect(head?.textContent).not.toContain("Articles");
    cleanup();
  });

  it("sends the reader back to the author's profile by default", async () => {
    const { container, cleanup } = await render({
      container: authorContainer(author),
      article: article({ project: null }),
      origin: { kind: "container", href: "/users/u-1#profile-articles", title: "Sigrún Haraldsdóttir" },
    });

    expect(container.querySelector('a[href="/users/u-1#profile-articles"]')?.textContent).toContain(
      "Sigrún Haraldsdóttir",
    );
    cleanup();
  });
});
