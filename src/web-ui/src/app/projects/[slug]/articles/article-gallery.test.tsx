import { describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import rehypePrismPlus from "rehype-prism-plus";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import remarkDirective from "remark-directive";
import remarkGfm from "remark-gfm";
import { ArticleGallery } from "./ArticleGallery";
import { galleryImagesFromElement } from "./gallery-hast";
import type { GalleryImage } from "./gallery-mdast";
import { remarkGallery } from "./remark-gallery";
import { articleSanitizeSchema } from "./sanitize-schema";

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

async function click(el: Element) {
  await act(async () => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

// The read page's pipeline, wired exactly as `ArticleRenderContent` wires it.
async function mountArticle(markdown: string) {
  return mount(
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkDirective, remarkGallery]}
      rehypePlugins={[
        rehypeRaw,
        [rehypePrismPlus, { ignoreMissing: true }],
        [rehypeSanitize, articleSanitizeSchema],
      ]}
      components={{
        div: ({ node, children, ...props }) => {
          const images = galleryImagesFromElement(node);
          return images ? (
            <ArticleGallery images={images} />
          ) : (
            <div {...props}>{children}</div>
          );
        },
      }}
    >
      {markdown}
    </ReactMarkdown>,
  );
}

// ------------------------------------------------------------------ queries

function buttonLabelled(container: HTMLElement, label: string): HTMLElement {
  return [...container.querySelectorAll("button")].find(
    (button) => button.getAttribute("aria-label") === label,
  )!;
}

function visibleImage(container: HTMLElement): HTMLImageElement | null {
  return container.querySelector(".article-gallery img");
}

function dots(container: HTMLElement): HTMLButtonElement[] {
  return [...container.querySelectorAll("button")].filter((button) =>
    button.getAttribute("aria-label")?.startsWith("Show image "),
  ) as HTMLButtonElement[];
}

function currentDotIndex(container: HTMLElement): number {
  return dots(container).findIndex(
    (dot) => dot.getAttribute("aria-current") === "true",
  );
}

// ----------------------------------------------------------------- factories

function galleryMarkdown(...srcs: string[]): string {
  const images = srcs
    .map((src, position) => `![Chart ${position + 1}](${src})`)
    .join("\n\n");
  return `:::gallery\n${images}\n:::\n`;
}

function anImage(overrides: Partial<GalleryImage> = {}): GalleryImage {
  return { src: "https://cdn.example/a.svg", alt: "A", ...overrides };
}

// -------------------------------------------------------------------- tests

describe("gallery blocks in the read pipeline", () => {
  it("renders a :::gallery block as a carousel showing the first image", async () => {
    const { container, unmount } = await mountArticle(
      galleryMarkdown("a.svg", "b.svg", "c.svg"),
    );

    expect(visibleImage(container)?.getAttribute("src")).toBe("a.svg");
    expect(dots(container)).toHaveLength(3);
    expect(container.textContent).toContain("1 / 3");

    unmount();
  });

  it("shows only the current image, not the whole block", async () => {
    const { container, unmount } = await mountArticle(
      galleryMarkdown("a.svg", "b.svg"),
    );

    expect(container.querySelectorAll("img")).toHaveLength(1);

    unmount();
  });

  it("uses the image alt text as the caption", async () => {
    const { container, unmount } = await mountArticle(
      galleryMarkdown("a.svg", "b.svg"),
    );

    expect(container.textContent).toContain("Chart 1");

    unmount();
  });

  it("also renders a hand-written div.gallery, since the class is allowed", async () => {
    const { container, unmount } = await mountArticle(
      '<div class="gallery">\n<img src="a.svg" alt="A">\n<img src="b.svg" alt="B">\n</div>\n',
    );

    expect(visibleImage(container)?.getAttribute("src")).toBe("a.svg");
    expect(dots(container)).toHaveLength(2);

    unmount();
  });

  it("leaves an ordinary div alone", async () => {
    const { container, unmount } = await mountArticle(
      '<div align="center">centred</div>\n',
    );

    expect(container.querySelector(".article-gallery")).toBeNull();
    expect(container.textContent).toContain("centred");

    unmount();
  });
});

describe("directives the gallery does not claim", () => {
  it("leaves a colon-wrapped word as literal text", async () => {
    const { container, unmount } = await mountArticle("I am :smile: today\n");

    expect(container.textContent).toContain(":smile:");

    unmount();
  });

  it("leaves an unknown container directive as its literal source", async () => {
    const { container, unmount } = await mountArticle(
      ":::note\nWatch out.\n:::\n",
    );

    expect(container.textContent).toContain(":::note");
    expect(container.textContent).toContain("Watch out.");
    expect(container.querySelector("note")).toBeNull();

    unmount();
  });

  it("leaves an unknown leaf directive as its literal source", async () => {
    const { container, unmount } = await mountArticle("::youtube{#abc}\n");

    expect(container.textContent).toContain("::youtube{#abc}");

    unmount();
  });
});

describe("ArticleGallery navigation", () => {
  const threeImages = [
    anImage({ src: "a.svg", alt: "A" }),
    anImage({ src: "b.svg", alt: "B" }),
    anImage({ src: "c.svg", alt: "C" }),
  ];

  it("advances to the next image", async () => {
    const { container, unmount } = await mount(
      <ArticleGallery images={threeImages} />,
    );

    await click(buttonLabelled(container, "Next image"));

    expect(visibleImage(container)?.getAttribute("src")).toBe("b.svg");
    expect(currentDotIndex(container)).toBe(1);

    unmount();
  });

  it("goes back to the previous image", async () => {
    const { container, unmount } = await mount(
      <ArticleGallery images={threeImages} />,
    );

    await click(buttonLabelled(container, "Next image"));
    await click(buttonLabelled(container, "Previous image"));

    expect(visibleImage(container)?.getAttribute("src")).toBe("a.svg");

    unmount();
  });

  it("jumps to an image from its dot", async () => {
    const { container, unmount } = await mount(
      <ArticleGallery images={threeImages} />,
    );

    await click(dots(container)[2]);

    expect(visibleImage(container)?.getAttribute("src")).toBe("c.svg");

    unmount();
  });

  it("disables the arrows at each end", async () => {
    const { container, unmount } = await mount(
      <ArticleGallery images={threeImages} />,
    );

    expect(buttonLabelled(container, "Previous image")).toHaveProperty(
      "disabled",
      true,
    );

    await click(dots(container)[2]);

    expect(buttonLabelled(container, "Next image")).toHaveProperty(
      "disabled",
      true,
    );

    unmount();
  });

  it("falls back to the last image when the list shrinks past the current one", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<ArticleGallery images={threeImages} />);
    });
    await click(dots(container)[2]);
    await act(async () => {
      root.render(<ArticleGallery images={threeImages.slice(0, 2)} />);
    });

    expect(visibleImage(container)?.getAttribute("src")).toBe("b.svg");
    expect(container.textContent).toContain("2 / 2");

    unmount(root, container);
  });

  it("renders nothing for an empty gallery in the read view", async () => {
    const { container, unmount } = await mount(<ArticleGallery images={[]} />);

    expect(container.querySelector(".article-gallery")).toBeNull();

    unmount();
  });
});
