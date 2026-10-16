import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { EdgeColor } from "./gallery-edge-color";
import type { GalleryImage } from "./gallery-mdast";

// jsdom has no canvas, so the real sampler can only ever answer null here.
// Standing in for it is the only way to exercise what a sampled colour does
// to the card.
const sampled = vi.hoisted(() => ({ value: null as EdgeColor | null }));
vi.mock("./gallery-edge-color", () => ({
  sampleEdgeColor: () => sampled.value,
}));

const { ArticleGallery } = await import("./ArticleGallery");

// ------------------------------------------------------------------ fixtures

const NEAR_WHITE: EdgeColor = { css: "rgb(250 250 247)", isDark: false };
const CHARCOAL: EdgeColor = { css: "rgb(24 26 32)", isDark: true };

const IMAGES: GalleryImage[] = [
  { src: "https://cdn.example/one.png", alt: "One" },
  { src: "https://cdn.example/two.png", alt: "Two" },
];

async function mountGallery(images: readonly GalleryImage[] = IMAGES) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<ArticleGallery images={images} />);
  });
  return { container, unmount: () => act(() => root.unmount()) };
}

// jsdom never fetches the image, so nothing would ever tell the gallery the
// pixels are there to read.
async function finishLoading(container: HTMLElement) {
  await act(async () => {
    container.querySelector("img")!.dispatchEvent(new Event("load"));
  });
}

const card = (container: HTMLElement) =>
  container.querySelector(".article-gallery") as HTMLElement;

const caption = (container: HTMLElement) =>
  container.querySelector(".tabular-nums")!.parentElement as HTMLElement;

// --------------------------------------------------------------------- tests

describe("gallery card fill", () => {
  beforeEach(() => {
    sampled.value = null;
  });

  it("keeps the default card background when the image yields no colour", async () => {
    const { container, unmount } = await mountGallery();
    await finishLoading(container);
    expect(card(container).style.backgroundColor).toBe("");
    expect(card(container).className).toContain("bg-muted/30");
    unmount();
  });

  it("paints the card with the colour sampled from the image", async () => {
    sampled.value = NEAR_WHITE;
    const { container, unmount } = await mountGallery();
    await finishLoading(container);
    expect(card(container).style.backgroundColor).toBe("rgb(250, 250, 247)");
    expect(card(container).className).not.toContain("bg-muted/30");
    unmount();
  });

  it("leaves the caption in its usual colour over a light fill", async () => {
    sampled.value = NEAR_WHITE;
    const { container, unmount } = await mountGallery();
    await finishLoading(container);
    expect(caption(container).className).toContain("text-muted-foreground");
    unmount();
  });

  it("turns the caption light over a dark fill", async () => {
    sampled.value = CHARCOAL;
    const { container, unmount } = await mountGallery();
    await finishLoading(container);
    expect(caption(container).className).toContain("text-white/70");
    expect(caption(container).className).not.toContain("text-muted-foreground");
    unmount();
  });

  it("turns the dots light over a dark fill", async () => {
    sampled.value = CHARCOAL;
    const { container, unmount } = await mountGallery();
    await finishLoading(container);
    const dots = [...container.querySelectorAll('[aria-label^="Show image"]')];
    expect(dots.map((d) => d.className.includes("bg-white"))).toEqual([true, true]);
    unmount();
  });

  it("requests the image anonymously so its pixels can be read back", async () => {
    const { container, unmount } = await mountGallery();
    expect(container.querySelector("img")!.getAttribute("crossorigin")).toBe("anonymous");
    unmount();
  });

  it("drops the anonymous request when the image fails to load that way", async () => {
    const { container, unmount } = await mountGallery();
    await act(async () => {
      container.querySelector("img")!.dispatchEvent(new Event("error"));
    });
    expect(container.querySelector("img")!.getAttribute("crossorigin")).toBeNull();
    unmount();
  });
});
