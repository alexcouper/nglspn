import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Article } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";
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

// Only the fields the preview reads; the rest of ProjectImage is irrelevant here.
function heroImage(
  overrides: { width: number | null; height: number | null } = {
    width: 4000,
    height: 2000,
  },
): Article["hero_image"] {
  return {
    id: "img-1",
    variants: [],
    ...overrides,
  } as unknown as Article["hero_image"];
}

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
    hero_image: heroImage(),
    hero_crop: null,
    card_crop: null,
    card_crop_display: null,
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

const CARD_CROP: CropRect = { x: 0.1, y: 0.2, w: 0.4, h: 0.45, ratio: 16 / 9 };
const DERIVED_CROP: CropRect = { x: 0, y: 0, w: 0.9, h: 1, ratio: 16 / 9 };

describe("toListItem", () => {
  it("prefers the authored summary over the derived one", () => {
    const item = toListItem(article({ summary: "Authored." }));

    expect(item.summary).toBe("Authored.");
  });

  it("falls back to summary_display when nothing is authored", () => {
    const item = toListItem(article({ summary: "" }));

    expect(item.summary).toBe("The body opening line.");
  });

  it("falls back to the derived card crop when there is no override", () => {
    const item = toListItem(
      article({ card_crop_display: DERIVED_CROP }),
      undefined,
      null,
    );

    expect(item.card_crop).toEqual(DERIVED_CROP);
  });

  it("prefers a card crop override over the derived one", () => {
    const item = toListItem(
      article({ card_crop_display: DERIVED_CROP }),
      undefined,
      CARD_CROP,
    );

    expect(item.card_crop).toEqual(CARD_CROP);
  });
});

describe("ArticleCardPreview", () => {
  it("shows the derived summary as a placeholder when none is authored", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        cardCrop={null}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
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
        cardCrop={null}
        onSummaryChange={onSummaryChange}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
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
        cardCrop={null}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
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
        cardCrop={null}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
      />,
    );

    expect(container.querySelectorAll("article").length).toBe(2);

    cleanup();
  });

  it("says the card follows the hero until an override is set", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        cardCrop={null}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
      />,
    );

    expect(container.textContent).toContain("Cards follow the hero framing.");
    expect(container.textContent).not.toContain("Reset to match hero");

    cleanup();
  });

  it("offers a reset once the card has its own framing", async () => {
    const onResetFraming = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        cardCrop={CARD_CROP}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={onResetFraming}
      />,
    );

    const reset = [...container.querySelectorAll("button")].find(
      (b) => b.textContent === "Reset to match hero",
    )!;
    await act(async () => {
      reset.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(onResetFraming).toHaveBeenCalledOnce();

    cleanup();
  });

  it("hides the framing controls when the hero has no recorded dimensions", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article({ hero_image: heroImage({ width: null, height: null }) })}
        summary=""
        cardCrop={null}
        onSummaryChange={() => {}}
        onAdjustFraming={() => {}}
        onResetFraming={() => {}}
      />,
    );

    expect(container.textContent).not.toContain("Adjust framing");

    cleanup();
  });
});
