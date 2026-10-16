import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { DirectiveEditorProps } from "@mdxeditor/editor";
import type { ContainerDirective } from "mdast-util-directive";
import { galleryDirectiveDescriptor } from "./GalleryDirectiveDescriptor";
import {
  galleryImagesFromMdast,
  galleryMdastFromImages,
  galleryWriteFor,
  type GalleryImage,
} from "./gallery-mdast";

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

function buttonLabelled(container: HTMLElement, label: string): HTMLElement {
  return [...container.querySelectorAll("button")].find(
    (button) => button.getAttribute("aria-label") === label,
  )!;
}

// ----------------------------------------------------------------- factories

function anImage(overrides: Partial<GalleryImage> = {}): GalleryImage {
  return { src: "https://cdn.example/a.svg", alt: "A", ...overrides };
}

/**
 * The descriptor's Editor with a stand-in for the Lexical node it edits.
 *
 * `parentEditor.update` runs its callback straight away rather than queueing
 * it, which is enough for the branches that only call `setMdastNode` — the
 * ones that construct Lexical nodes need a real editor and are covered by
 * `galleryWriteFor` below and by the e2e spec.
 */
async function mountGalleryEditor(images: GalleryImage[]) {
  const setMdastNode = vi.fn();
  const remove = vi.fn();
  const replace = vi.fn();

  const props = {
    mdastNode: galleryMdastFromImages(images),
    lexicalNode: { setMdastNode, remove, replace },
    parentEditor: { update: (fn: () => void) => fn() },
    descriptor: galleryDirectiveDescriptor,
  } as unknown as DirectiveEditorProps<ContainerDirective>;

  const Editor = galleryDirectiveDescriptor.Editor;
  const { container, unmount } = await mount(<Editor {...props} />);
  return {
    container,
    unmount,
    setMdastNode,
    remove,
    replace,
    /** The images the editor wrote back, read out of the mdast it produced. */
    writtenImages: () =>
      galleryImagesFromMdast(setMdastNode.mock.calls.at(-1)![0]),
  };
}

// -------------------------------------------------------------------- tests

describe("galleryWriteFor", () => {
  it("keeps a gallery while more than one image is left", () => {
    const images = [anImage({ src: "a.svg" }), anImage({ src: "b.svg" })];

    expect(galleryWriteFor(images)).toEqual({ kind: "update", images });
  });

  it("collapses to a plain image when one is left", () => {
    const image = anImage({ src: "a.svg" });

    expect(galleryWriteFor([image])).toEqual({ kind: "collapse", image });
  });

  it("removes the block when the last image goes", () => {
    expect(galleryWriteFor([])).toEqual({ kind: "remove" });
  });
});

describe("the gallery editor's per-image controls", () => {
  const threeImages = [
    anImage({ src: "a.svg", alt: "A" }),
    anImage({ src: "b.svg", alt: "B" }),
    anImage({ src: "c.svg", alt: "C" }),
  ];

  it("nudges the current image one place right", async () => {
    const editor = await mountGalleryEditor(threeImages);

    await click(buttonLabelled(editor.container, "Move image right"));

    expect(editor.writtenImages().map((image) => image.src)).toEqual([
      "b.svg",
      "a.svg",
      "c.svg",
    ]);

    editor.unmount();
  });

  it("nudges the current image one place left", async () => {
    const editor = await mountGalleryEditor(threeImages);

    await click(buttonLabelled(editor.container, "Show image 2"));
    await click(buttonLabelled(editor.container, "Move image left"));

    expect(editor.writtenImages().map((image) => image.src)).toEqual([
      "b.svg",
      "a.svg",
      "c.svg",
    ]);

    editor.unmount();
  });

  it("removes the current image from the gallery", async () => {
    const editor = await mountGalleryEditor(threeImages);

    await click(buttonLabelled(editor.container, "Show image 2"));
    await click(buttonLabelled(editor.container, "Remove image from gallery"));

    expect(editor.writtenImages().map((image) => image.src)).toEqual([
      "a.svg",
      "c.svg",
    ]);

    editor.unmount();
  });

  it("cannot nudge the first image left or the last one right", async () => {
    const editor = await mountGalleryEditor(threeImages);

    expect(buttonLabelled(editor.container, "Move image left")).toHaveProperty(
      "disabled",
      true,
    );

    await click(buttonLabelled(editor.container, "Show image 3"));

    expect(buttonLabelled(editor.container, "Move image right")).toHaveProperty(
      "disabled",
      true,
    );

    editor.unmount();
  });

  it("tells the author they can drop images onto it", async () => {
    const editor = await mountGalleryEditor(threeImages);

    expect(editor.container.textContent).toContain("Drop an image here");

    editor.unmount();
  });
});
