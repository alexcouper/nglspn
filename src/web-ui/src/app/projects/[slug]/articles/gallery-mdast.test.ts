import { describe, expect, it } from "vitest";
import { remark } from "remark";
import remarkDirective from "remark-directive";
import type { Root } from "mdast";
import type { ContainerDirective } from "mdast-util-directive";
import {
  galleryImagesFromMdast,
  galleryMdastFromImages,
  isGalleryDirective,
  moveGalleryImage,
  removeGalleryImage,
  type GalleryImage,
} from "./gallery-mdast";

// The same parser/serialiser pair the read pipeline and MDXEditor both use,
// so a round-trip assertion here means the markdown we write is the markdown
// they will read back.
const processor = remark().use(remarkDirective);

function parse(markdown: string): Root {
  return processor.parse(markdown);
}

function serialize(root: Root): string {
  return processor.stringify(root);
}

function firstDirective(markdown: string): ContainerDirective {
  const node = parse(markdown).children[0];
  if (node.type !== "containerDirective") {
    throw new Error(`expected a container directive, got ${node.type}`);
  }
  return node;
}

function anImage(overrides: Partial<GalleryImage> = {}): GalleryImage {
  return { src: "https://cdn.example/a.svg", alt: "A", ...overrides };
}

describe("isGalleryDirective", () => {
  it("recognises a container directive named gallery", () => {
    expect(isGalleryDirective(firstDirective(":::gallery\n:::\n"))).toBe(true);
  });

  it("rejects a container directive with another name", () => {
    expect(isGalleryDirective(firstDirective(":::note\n:::\n"))).toBe(false);
  });
});

describe("galleryImagesFromMdast", () => {
  it("collects images written on consecutive lines", () => {
    const images = galleryImagesFromMdast(
      firstDirective(":::gallery\n![A](a.svg)\n![B](b.svg)\n:::\n"),
    );

    expect(images).toEqual([
      { src: "a.svg", alt: "A" },
      { src: "b.svg", alt: "B" },
    ]);
  });

  it("collects images separated by blank lines", () => {
    const images = galleryImagesFromMdast(
      firstDirective(":::gallery\n![A](a.svg)\n\n![B](b.svg)\n:::\n"),
    );

    expect(images.map((image) => image.src)).toEqual(["a.svg", "b.svg"]);
  });

  it("keeps an image title", () => {
    const images = galleryImagesFromMdast(
      firstDirective(':::gallery\n![A](a.svg "Cost of living")\n:::\n'),
    );

    expect(images[0]).toEqual({
      src: "a.svg",
      alt: "A",
      title: "Cost of living",
    });
  });

  it("ignores prose the author left inside the block", () => {
    const images = galleryImagesFromMdast(
      firstDirective(":::gallery\nsome stray text\n\n![A](a.svg)\n:::\n"),
    );

    expect(images.map((image) => image.src)).toEqual(["a.svg"]);
  });

  it("returns nothing for an empty gallery", () => {
    expect(galleryImagesFromMdast(firstDirective(":::gallery\n:::\n"))).toEqual(
      [],
    );
  });
});

describe("galleryMdastFromImages", () => {
  it("serialises to a gallery directive with one image per paragraph", () => {
    const node = galleryMdastFromImages([
      { src: "a.svg", alt: "A" },
      { src: "b.svg", alt: "B" },
    ]);

    expect(serialize({ type: "root", children: [node] })).toBe(
      ":::gallery\n![A](a.svg)\n\n![B](b.svg)\n:::\n",
    );
  });

  it("round-trips images unchanged", () => {
    const images = [
      { src: "a.svg", alt: "A", title: "First" },
      { src: "b.svg", alt: "" },
    ];

    const markdown = serialize({
      type: "root",
      children: [galleryMdastFromImages(images)],
    });

    expect(galleryImagesFromMdast(firstDirective(markdown))).toEqual(images);
  });
});

describe("moveGalleryImage", () => {
  const images = [
    anImage({ src: "a.svg" }),
    anImage({ src: "b.svg" }),
    anImage({ src: "c.svg" }),
  ];

  it("nudges an image one place left", () => {
    expect(moveGalleryImage(images, 1, 0).map((i) => i.src)).toEqual([
      "b.svg",
      "a.svg",
      "c.svg",
    ]);
  });

  it("nudges an image one place right", () => {
    expect(moveGalleryImage(images, 1, 2).map((i) => i.src)).toEqual([
      "a.svg",
      "c.svg",
      "b.svg",
    ]);
  });

  it("leaves the list alone when the target is out of range", () => {
    expect(moveGalleryImage(images, 0, -1)).toEqual(images);
    expect(moveGalleryImage(images, 2, 3)).toEqual(images);
  });

  it("does not mutate the input", () => {
    const original = [...images];
    moveGalleryImage(images, 0, 2);
    expect(images).toEqual(original);
  });
});

describe("removeGalleryImage", () => {
  it("drops the image at the index", () => {
    const remaining = removeGalleryImage(
      [anImage({ src: "a.svg" }), anImage({ src: "b.svg" })],
      0,
    );

    expect(remaining.map((image) => image.src)).toEqual(["b.svg"]);
  });

  it("does not mutate the input", () => {
    const images = [anImage({ src: "a.svg" }), anImage({ src: "b.svg" })];
    removeGalleryImage(images, 0);
    expect(images).toHaveLength(2);
  });
});
