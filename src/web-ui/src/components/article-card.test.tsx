import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { ArticleListItem } from "@/lib/api";
import { ArticleHeroImage } from "./ArticleHeroImage";
import { ArticleCard } from "./ArticleCard";

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- factories

function articleListItem(
  overrides: Partial<ArticleListItem> = {},
): ArticleListItem {
  return {
    id: "article-1",
    title: "A headline about something",
    summary: "A short summary of the article.",
    slug: "a-headline",
    state: "published",
    published_at: "2026-08-01T10:00:00Z",
    global_visibility: "auto",
    channel: { id: "channel-1", name: "Releases" },
    hero_image_url: "https://cdn.example/hero.png",
    ...overrides,
  } as ArticleListItem;
}

// ---------------------------------------------------------------- the tests

describe("ArticleHeroImage", () => {
  it("crops to 16:9 so a wide upload is not squashed into a square", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleHeroImage
        src="https://cdn.example/hero.png"
        alt="A screenshot"
        articleId="article-1"
      />,
    );

    const img = container.querySelector("img")!;
    expect(img.getAttribute("src")).toBe("https://cdn.example/hero.png");
    expect(img.className).toContain("object-cover");
    expect(container.querySelector(".aspect-\\[16\\/9\\]")).not.toBeNull();

    cleanup();
  });

  it("falls back to a gradient placeholder when there is no image", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleHeroImage src={null} alt="" articleId="article-1" />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector(".aspect-\\[16\\/9\\]")).not.toBeNull();

    cleanup();
  });

  it("loads eagerly when marked priority and lazily otherwise", async () => {
    const eager = await mount(
      <ArticleHeroImage src="/a.png" alt="" articleId="a" priority />,
    );
    expect(eager.container.querySelector("img")!.getAttribute("loading")).toBe(
      "eager",
    );
    eager.unmount();

    const lazy = await mount(
      <ArticleHeroImage src="/b.png" alt="" articleId="b" />,
    );
    expect(lazy.container.querySelector("img")!.getAttribute("loading")).toBe(
      "lazy",
    );
    lazy.unmount();
  });
});

describe("ArticleCard", () => {
  it("renders the headline, channel and summary, linking to the article", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCard
        article={articleListItem()}
        href="/projects/p/articles/a-headline"
        variant="grid"
      />,
    );

    const link = container.querySelector("a")!;
    expect(link.getAttribute("href")).toBe("/projects/p/articles/a-headline");
    expect(container.textContent).toContain("A headline about something");
    expect(container.textContent).toContain("Releases");
    expect(container.textContent).toContain("A short summary of the article.");

    cleanup();
  });

  it("gives the lead variant a larger headline than the grid variant", async () => {
    const lead = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="lead" />,
    );
    expect(lead.container.querySelector("h3")!.className).toContain("text-2xl");
    lead.unmount();

    const grid = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="grid" />,
    );
    expect(grid.container.querySelector("h3")!.className).toContain("text-base");
    grid.unmount();
  });

  it("loads the lead hero eagerly and grid heroes lazily", async () => {
    const lead = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="lead" />,
    );
    expect(lead.container.querySelector("img")!.getAttribute("loading")).toBe(
      "eager",
    );
    lead.unmount();

    const grid = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="grid" />,
    );
    expect(grid.container.querySelector("img")!.getAttribute("loading")).toBe(
      "lazy",
    );
    grid.unmount();
  });

  it("renders without a summary or a published date", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCard
        article={articleListItem({ summary: "", published_at: null })}
        href="/x"
        variant="grid"
      />,
    );

    expect(container.textContent).toContain("A headline about something");

    cleanup();
  });
});
