import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Article } from "@/lib/api";
import { ArticleCardPreview, toListItem } from "./ArticleCardPreview";

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

async function typeInto(el: HTMLTextAreaElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "value",
  )!.set!;
  await act(async () => {
    setValue.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

// --------------------------------------------------------------- factories

function article(overrides: Partial<Article> = {}): Article {
  return {
    id: "article-1",
    project: { id: "p1", slug: "proj", title: "A project" },
    channel: { id: "c1", name: "Releases" },
    author: null,
    title: "A headline",
    body: "The body opening line.",
    summary: "",
    summary_display: "The body opening line.",
    hero_image_id: "img-1",
    hero_image_url: "https://cdn.example/hero.png",
    slug: "a-headline",
    source: "internal",
    external_url: null,
    state: "draft",
    published_at: null,
    global_visibility: "auto",
    is_globally_visible: false,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  } as Article;
}

// ---------------------------------------------------------------- the tests

describe("toListItem", () => {
  it("prefers the authored summary over the derived one", () => {
    const item = toListItem(article({ summary: "Authored." }));

    expect(item.summary).toBe("Authored.");
  });

  it("falls back to summary_display when nothing is authored", () => {
    const item = toListItem(article({ summary: "" }));

    expect(item.summary).toBe("The body opening line.");
  });
});

describe("ArticleCardPreview", () => {
  it("shows the derived summary as a placeholder when none is authored", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={() => {}}
      />,
    );

    const textarea = container.querySelector("textarea")!;
    expect(textarea.value).toBe("");
    expect(textarea.getAttribute("placeholder")).toBe("The body opening line.");

    cleanup();
  });

  it("reports typed text back to its owner", async () => {
    const onSummaryChange = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={onSummaryChange}
      />,
    );

    await typeInto(container.querySelector("textarea")!, "An authored hook.");

    expect(onSummaryChange).toHaveBeenCalledWith("An authored hook.");

    cleanup();
  });

  it("previews the typed summary rather than the derived one", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary="An authored hook."
        onSummaryChange={() => {}}
      />,
    );

    expect(container.textContent).toContain("An authored hook.");

    cleanup();
  });

  it("renders both a lead and a grid card", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        onSummaryChange={() => {}}
      />,
    );

    expect(container.querySelectorAll("article").length).toBe(2);

    cleanup();
  });
});
