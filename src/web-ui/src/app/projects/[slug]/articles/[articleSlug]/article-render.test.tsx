import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Article, Project } from "@/lib/api";

import { ArticleRenderContent } from "./ArticleRenderContent";
import type { Onward } from "./onward";

// The component reads auth to decide whether to mark the article read, and
// calls the notifications context when it does. Neither is what these tests
// are about, so both are stubbed at the module boundary.
vi.mock("@/contexts/auth", () => ({
  useAuth: () => ({ isAuthenticated: false, isLoading: false }),
}));
vi.mock("@/contexts/notifications", () => ({
  useNotifications: () => ({ markArticleRead: vi.fn().mockResolvedValue(undefined) }),
}));

// ------------------------------------------------------------------ fixtures

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

function onward(overrides: Partial<Onward> = {}): Onward {
  return {
    heading: "More in Updates",
    moreHref: "/projects/hot-spring-finder#articles",
    moreLabel: "All 4 articles from Hot Spring Finder",
    lead: {
      id: "a-2",
      href: "/projects/hot-spring-finder/articles/offline-tiles",
      flag: "Updates",
      title: "Offline tiles",
      summary: "A storage problem.",
      imageUrl: null,
      crop: null,
    },
    rest: [],
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
        project={project()}
        article={article()}
        origin={{ href: "/latest", label: "Latest" }}
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

function backLink(container: HTMLElement): HTMLAnchorElement | null {
  return container.querySelector('a[href="/latest"], a[href^="/projects/"][href$="#articles"]');
}

// --------------------------------------------------------------------- tests

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
        href: "/projects/hot-spring-finder#articles",
        label: "Hot Spring Finder",
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
