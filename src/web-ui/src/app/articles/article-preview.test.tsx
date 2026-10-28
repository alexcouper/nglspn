import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { Article, Project } from "@/lib/api";
import { ArticlePreview } from "./ArticlePreview";
import { projectContainer } from "./container";

vi.mock("@/contexts/auth", () => ({
  useAuth: () => ({ isAuthenticated: true, isLoading: false }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
}));
const markArticleRead = vi.fn().mockResolvedValue(undefined);
vi.mock("@/contexts/notifications", () => ({
  useNotifications: () => ({ markArticleRead }),
}));

function project(): Project {
  return {
    id: "p-1",
    slug: "hot-spring-finder",
    title: "Hot Spring Finder",
    images: [],
  } as unknown as Project;
}

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "a-1",
    title: "We mapped 94 unmarked hot springs",
    body: "The first version had 212 pins on it.",
    summary: "",
    summary_display: "The first version had 212 pins on it.",
    slug: null,
    state: "draft",
    published_at: null,
    global_visibility: "auto",
    is_globally_visible: false,
    channel: { id: "ch-1", name: "Updates" },
    author: null,
    listing_image_url: "https://example.test/cover.jpg",
    listing_crop: null,
    ...overrides,
  } as Article;
}

async function mount(a: Article = article()) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<ArticlePreview article={a} container={projectContainer(project())} />);
  });
  return {
    container,
    tab: (name: string) => {
      const tab = Array.from(container.querySelectorAll('[role="tab"]')).find(
        (el) => el.textContent === name,
      ) as HTMLButtonElement | undefined;
      if (!tab) throw new Error(`no tab ${name}`);
      act(() => tab.click());
    },
    cleanup: () => {
      act(() => root.unmount());
      container.remove();
    },
  };
}

describe("ArticlePreview", () => {
  it("opens on the article itself, rendered as the page renders it", async () => {
    const { container, cleanup } = await mount();

    expect(container.querySelector("h1")?.textContent).toBe(
      "We mapped 94 unmarked hot springs",
    );
    expect(
      container.querySelector('[data-testid="article-listing-image"]'),
    ).not.toBeNull();
    expect(container.textContent).toContain("Draft");
    cleanup();
  });

  it("does not mark the author's own draft as read", async () => {
    const { cleanup } = await mount();

    expect(markArticleRead).not.toHaveBeenCalled();
    cleanup();
  });

  it("switches to the lead and grid cards", async () => {
    const { container, tab, cleanup } = await mount();

    tab("As lead story");
    expect(container.querySelector('[data-testid="preview-article"]')).toBeNull();
    expect(container.querySelector("article")?.textContent).toContain(
      "We mapped 94 unmarked hot springs",
    );

    tab("In the grid");
    expect(container.querySelector(".max-w-sm article")).not.toBeNull();
    cleanup();
  });

  it("shows a text-only card for an article without a cover", async () => {
    const { container, tab, cleanup } = await mount(
      article({ listing_image_url: null }),
    );

    tab("In the grid");
    expect(container.querySelector("article img")).toBeNull();
    cleanup();
  });
});
