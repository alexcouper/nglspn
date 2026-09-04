import { SKIP, visit } from "unist-util-visit";
import type { Paragraph, Root, RootContent, Text } from "mdast";
import type { Directives } from "mdast-util-directive";
import {
  GALLERY_CLASS,
  galleryImagesFromMdast,
  isGalleryDirective,
  type GalleryImage,
} from "./gallery-mdast";

const DIRECTIVE_TYPES = new Set([
  "containerDirective",
  "leafDirective",
  "textDirective",
]);

function isDirective(node: { type: string }): node is Directives {
  return DIRECTIVE_TYPES.has(node.type);
}

function galleryElement(images: readonly GalleryImage[]): RootContent {
  return {
    type: "paragraph",
    data: {
      hName: "div",
      hProperties: { className: [GALLERY_CLASS] },
    },
    children: images.map((image) => ({
      type: "image",
      url: image.src,
      alt: image.alt,
      ...(image.title ? { title: image.title } : {}),
    })),
  } satisfies Paragraph;
}

// `remark-directive` claims every `:name`, `::name` and `:::name` in the
// source, including the ones nobody meant as a directive — `:smile:` in prose
// or a line of `:::` used as a separator. Articles predate this plugin, so
// anything we do not recognise is put back as the exact source text it was
// parsed from, and the read view for an existing article does not move.
function literalReplacement(node: Directives, source: string): RootContent {
  const start = node.position?.start.offset;
  const end = node.position?.end.offset;
  const value =
    start === undefined || end === undefined
      ? `:${node.name}`
      : source.slice(start, end);

  const text: Text = { type: "text", value };
  // Text is not block content, so a leaf or container directive — both of
  // which sit between paragraphs — needs a paragraph to live in.
  return node.type === "textDirective"
    ? text
    : ({ type: "paragraph", children: [text] } satisfies Paragraph);
}

/**
 * Renders `:::gallery` blocks as `<div class="gallery">` holding the block's
 * images, and restores every other directive to its literal source text.
 *
 * Must run after `remark-directive`, which is what produces the nodes.
 */
export function remarkGallery() {
  return (tree: Root, file: { toString(): string }) => {
    const source = file.toString();

    visit(tree, (node, index, parent) => {
      if (!isDirective(node) || parent === undefined || index === undefined) {
        return;
      }

      parent.children[index] = isGalleryDirective(node)
        ? galleryElement(galleryImagesFromMdast(node))
        : literalReplacement(node, source);

      // The replacement's children are already final — the images we lifted
      // out, or a single text node. Descending into the original node's
      // children would visit nodes that are no longer in the tree.
      return SKIP;
    });
  };
}
