import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { Article, ProjectImage } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";
import { ArticleCardPreview, toListItem } from "./ArticleCardPreview";
import { ListingSettingsPanel } from "./ListingSettingsPanel";

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

async function click(el: Element) {
  await act(async () => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function buttonLabelled(container: HTMLElement, label: string): HTMLElement {
  return [...container.querySelectorAll("button")].find(
    (b) => b.textContent?.trim() === label,
  )!;
}

// --------------------------------------------------------------- factories

// Only the fields these components read; the rest of ProjectImage is
// irrelevant here.
function listingImage(
  overrides: Partial<ProjectImage> = {},
): ProjectImage {
  return {
    id: "img-1",
    url: "https://cdn.example/listing.png",
    original_filename: "listing.png",
    width: 4000,
    height: 2000,
    variants: [],
    ...overrides,
  } as unknown as ProjectImage;
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
    listing_image_id: "img-1",
    listing_image_url: "https://cdn.example/listing.png",
    listing_image: listingImage(),
    listing_crop: null,
    listing_image_mode: "auto",
    images: [listingImage()],
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

const LISTING_CROP: CropRect = { x: 0.1, y: 0.2, w: 0.4, h: 0.225, ratio: 16 / 9 };

function panel(overrides: Partial<React.ComponentProps<typeof ListingSettingsPanel>> = {}) {
  return (
    <ListingSettingsPanel
      article={article()}
      summary=""
      listingImage={listingImage()}
      crop={null}
      mode="auto"
      onSummaryChange={() => {}}
      onChangeImage={() => {}}
      onRemoveImage={() => {}}
      {...overrides}
    />
  );
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

  it("takes the unsaved image and crop over the saved ones", () => {
    const item = toListItem(
      article(),
      undefined,
      "https://cdn.example/other.png",
      LISTING_CROP,
    );

    expect(item.listing_image_url).toBe("https://cdn.example/other.png");
    expect(item.listing_crop).toEqual(LISTING_CROP);
  });

  it("carries an explicit null image through rather than falling back", () => {
    const item = toListItem(article(), undefined, null, null);

    expect(item.listing_image_url).toBeNull();
  });
});

describe("ArticleCardPreview", () => {
  it("shows one variant at a time, starting with the lead card", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        imageUrl="https://cdn.example/listing.png"
        crop={null}
      />,
    );

    expect(container.querySelectorAll("article").length).toBe(1);
    expect(
      buttonLabelled(container, "As lead story").getAttribute("aria-selected"),
    ).toBe("true");

    cleanup();
  });

  it("switches to the grid card without showing the lead one as well", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary=""
        imageUrl="https://cdn.example/listing.png"
        crop={null}
      />,
    );

    await click(buttonLabelled(container, "In the grid"));

    expect(container.querySelectorAll("article").length).toBe(1);
    expect(
      buttonLabelled(container, "In the grid").getAttribute("aria-selected"),
    ).toBe("true");
    expect(
      buttonLabelled(container, "As lead story").getAttribute("aria-selected"),
    ).toBe("false");

    cleanup();
  });

  it("previews the typed summary rather than the derived one", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCardPreview
        article={article()}
        summary="An authored hook."
        imageUrl={null}
        crop={null}
      />,
    );

    expect(container.textContent).toContain("An authored hook.");

    cleanup();
  });
});

describe("ListingSettingsPanel", () => {
  it("shows the derived summary as a placeholder when none is authored", async () => {
    const { container, unmount: cleanup } = await mount(panel());

    const textarea = container.querySelector("textarea")!;
    expect(textarea.value).toBe("");
    expect(textarea.getAttribute("placeholder")).toBe("The body opening line.");

    cleanup();
  });

  it("reports typed text back to its owner", async () => {
    const onSummaryChange = vi.fn();
    const { container, unmount: cleanup } = await mount(
      panel({ onSummaryChange }),
    );

    await typeInto(container.querySelector("textarea")!, "An authored hook.");

    expect(onSummaryChange).toHaveBeenCalledWith("An authored hook.");

    cleanup();
  });

  it("says the image is following the article rather than chosen", async () => {
    const { container, unmount: cleanup } = await mount(panel({ mode: "auto" }));

    expect(container.textContent).toContain(
      "Following the first image in this article.",
    );

    cleanup();
  });

  it("says the image is the author's own choice", async () => {
    const { container, unmount: cleanup } = await mount(
      panel({ mode: "chosen", crop: LISTING_CROP }),
    );

    expect(container.textContent).toContain("Your choice.");

    cleanup();
  });

  it("says an article shows no image once one has been removed", async () => {
    const { container, unmount: cleanup } = await mount(
      panel({ mode: "none", listingImage: null }),
    );

    expect(container.textContent).toContain(
      "This article shows no image in listings.",
    );

    cleanup();
  });

  it("offers Remove until the image is already removed", async () => {
    const withImage = await mount(panel({ mode: "auto" }));
    expect(buttonLabelled(withImage.container, "Remove")).toBeDefined();
    withImage.unmount();

    const removed = await mount(panel({ mode: "none", listingImage: null }));
    expect(buttonLabelled(removed.container, "Remove")).toBeUndefined();
    removed.unmount();
  });

  it("opens the wizard from Change", async () => {
    const onChangeImage = vi.fn();
    const { container, unmount: cleanup } = await mount(
      panel({ onChangeImage }),
    );

    await click(buttonLabelled(container, "Change…"));

    expect(onChangeImage).toHaveBeenCalledOnce();

    cleanup();
  });
});
