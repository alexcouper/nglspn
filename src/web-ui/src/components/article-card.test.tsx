import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { ArticleListItem } from "@/lib/api";
import { ArticleListingImage } from "./ArticleListingImage";
import { ArticleCard } from "./ArticleCard";
import { CroppedImage, type CropRect } from "./CroppedImage";

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
    listing_image_url: "https://cdn.example/listing.png",
    listing_crop: null,
    ...overrides,
  } as ArticleListItem;
}

// A 2:1 selection covering the middle-left of the source.
function crop(overrides: Partial<CropRect> = {}): CropRect {
  return { x: 0.1, y: 0.25, w: 0.5, h: 0.25, ratio: 2, ...overrides };
}

function frameOf(container: HTMLElement): HTMLElement {
  return container.firstElementChild as HTMLElement;
}

// ---------------------------------------------------------------- the tests

describe("CroppedImage", () => {
  it("scales and offsets the image so the crop fills the box", async () => {
    const { container, unmount: cleanup } = await mount(
      <CroppedImage src="/a.png" alt="" crop={crop()} />,
    );

    const img = container.querySelector("img")!;
    // w=0.5 -> the source is twice the box; x=0.1 -> shifted by a fifth of it.
    expect(img.style.width).toBe("200%");
    expect(img.style.height).toBe("400%");
    expect(img.style.left).toBe("-20%");
    expect(img.style.top).toBe("-100%");
    expect(frameOf(container).style.aspectRatio).toBe("2");

    cleanup();
  });

  it("sets max-width inline so a global image reset cannot shift the crop", async () => {
    const { container, unmount: cleanup } = await mount(
      <CroppedImage src="/a.png" alt="" crop={crop()} />,
    );

    expect(container.querySelector("img")!.style.maxWidth).toBe("none");

    cleanup();
  });

  it("falls back to a 16:9 centre cover when there is no crop", async () => {
    const { container, unmount: cleanup } = await mount(
      <CroppedImage src="/a.png" alt="" crop={null} />,
    );

    const img = container.querySelector("img")!;
    expect(img.className).toContain("object-cover");
    expect(img.style.width).toBe("");
    expect(frameOf(container).style.aspectRatio).toBe(String(16 / 9));

    cleanup();
  });
});

describe("ArticleListingImage", () => {
  it("renders at the stored ratio rather than a fixed shape", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleListingImage
        src="https://cdn.example/listing.png"
        alt="A screenshot"
        crop={crop({ ratio: 2.8333 })}
      />,
    );

    expect(container.querySelector("img")!.getAttribute("src")).toBe(
      "https://cdn.example/listing.png",
    );
    expect(frameOf(container).style.aspectRatio).toBe("2.8333");

    cleanup();
  });

  it("crops to 16:9 so an uncropped wide upload is not squashed into a square", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleListingImage
        src="https://cdn.example/listing.png"
        alt="A screenshot"
      />,
    );

    const img = container.querySelector("img")!;
    expect(img.className).toContain("object-cover");
    expect(frameOf(container).style.aspectRatio).toBe(String(16 / 9));

    cleanup();
  });

  it("renders nothing at all when there is no image", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleListingImage src={null} alt="" />,
    );

    expect(container.innerHTML).toBe("");

    cleanup();
  });

  it("loads eagerly when marked priority and lazily otherwise", async () => {
    const eager = await mount(
      <ArticleListingImage src="/a.png" alt="" priority />,
    );
    expect(eager.container.querySelector("img")!.getAttribute("loading")).toBe(
      "eager",
    );
    eager.unmount();

    const lazy = await mount(<ArticleListingImage src="/b.png" alt="" />);
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

  it("loads the lead image eagerly and grid images lazily", async () => {
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

  it("draws no image element at all for an article with no listing image", async () => {
    const { container, unmount: cleanup } = await mount(
      <ArticleCard
        article={articleListItem({ listing_image_url: null })}
        href="/x"
        variant="grid"
      />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).toBeNull();

    cleanup();
  });

  it("gives an imageless card wider clamps than an imaged one", async () => {
    const bare = await mount(
      <ArticleCard
        article={articleListItem({ listing_image_url: null })}
        href="/x"
        variant="grid"
      />,
    );
    expect(bare.container.querySelector("h3")!.className).toContain(
      "line-clamp-4",
    );
    expect(bare.container.querySelector("p")!.className).toContain(
      "line-clamp-5",
    );
    bare.unmount();

    const imaged = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="grid" />,
    );
    expect(imaged.container.querySelector("h3")!.className).toContain(
      "line-clamp-2",
    );
    expect(imaged.container.querySelector("p")!.className).toContain(
      "line-clamp-3",
    );
    imaged.unmount();
  });

  it("marks an imageless lead card so it does not read as a failed image", async () => {
    const bare = await mount(
      <ArticleCard
        article={articleListItem({ listing_image_url: null })}
        href="/x"
        variant="lead"
      />,
    );
    expect(bare.container.querySelector(".bg-accent")).not.toBeNull();
    expect(bare.container.querySelector("h3")!.className).toContain("text-3xl");
    bare.unmount();

    const imaged = await mount(
      <ArticleCard article={articleListItem()} href="/x" variant="lead" />,
    );
    expect(imaged.container.querySelector(".bg-accent")).toBeNull();
    imaged.unmount();
  });
});
