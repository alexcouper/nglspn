import type { Image, Node, Parent } from "mdast";
import type { ContainerDirective } from "mdast-util-directive";

// An article gallery is a container directive holding ordinary markdown
// images:
//
//     :::gallery
//     ![Cost of living](https://…/01.svg)
//
//     ![Events](https://…/02.svg)
//     :::
//
// Keeping the images as real markdown image nodes is the point of the shape:
// reordering is reordering lines, deleting is deleting a line, and anything
// that walks the article body (summary derivation, a future feed) still sees
// the images rather than an opaque blob.
export const GALLERY_DIRECTIVE_NAME = "gallery";

// The class `remark-gallery` puts on the wrapper it builds, and the one
// block-level class `sanitize-schema.ts` lets through.
export const GALLERY_CLASS = "gallery";

export interface GalleryImage {
  src: string;
  alt: string;
  title?: string;
}

export function isGalleryDirective(node: Node): node is ContainerDirective {
  return (
    node.type === "containerDirective" &&
    (node as ContainerDirective).name === GALLERY_DIRECTIVE_NAME
  );
}

function hasChildren(node: Node): node is Parent {
  return "children" in node && Array.isArray((node as Parent).children);
}

// Reading is deliberately tolerant: it takes every image anywhere under the
// directive, in document order, whatever the author's line breaks did to the
// paragraph structure, and ignores anything that is not an image. Writing
// (below) is the strict half.
export function galleryImagesFromMdast(node: ContainerDirective): GalleryImage[] {
  const images: GalleryImage[] = [];

  const collect = (current: Node) => {
    if (current.type === "image") {
      const image = current as Image;
      images.push({
        src: image.url,
        alt: image.alt ?? "",
        ...(image.title ? { title: image.title } : {}),
      });
      return;
    }
    if (hasChildren(current)) current.children.forEach(collect);
  };

  node.children.forEach(collect);
  return images;
}

// One image per paragraph, so the serialised markdown puts a blank line
// between them. Consecutive image lines would parse back into a single
// paragraph joined by text nodes, which survives a round-trip but drifts in
// whitespace every time the editor rewrites the block.
export function galleryMdastFromImages(
  images: readonly GalleryImage[],
): ContainerDirective {
  return {
    type: "containerDirective",
    name: GALLERY_DIRECTIVE_NAME,
    attributes: {},
    children: images.map((image) => ({
      type: "paragraph",
      children: [
        {
          type: "image",
          url: image.src,
          alt: image.alt,
          ...(image.title ? { title: image.title } : {}),
        },
      ],
    })),
  };
}

export function moveGalleryImage(
  images: readonly GalleryImage[],
  from: number,
  to: number,
): GalleryImage[] {
  if (to < 0 || to >= images.length || from < 0 || from >= images.length) {
    return [...images];
  }
  const moved = [...images];
  const [image] = moved.splice(from, 1);
  moved.splice(to, 0, image);
  return moved;
}

export function removeGalleryImage(
  images: readonly GalleryImage[],
  index: number,
): GalleryImage[] {
  return images.filter((_, position) => position !== index);
}

// What removing or reordering leaves behind. Kept separate from the editor
// component so the rule — a carousel of one is just an image — is stated once
// and can be tested without a Lexical editor to run it in.
export type GalleryWrite =
  | { kind: "update"; images: GalleryImage[] }
  | { kind: "collapse"; image: GalleryImage }
  | { kind: "remove" };

export function galleryWriteFor(images: readonly GalleryImage[]): GalleryWrite {
  if (images.length > 1) return { kind: "update", images: [...images] };
  if (images.length === 1) return { kind: "collapse", image: images[0] };
  return { kind: "remove" };
}
