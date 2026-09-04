import { SKIP, visit } from "unist-util-visit";
import type { Paragraph, Root, RootContent } from "mdast";
import type { ContainerDirective, Directives } from "mdast-util-directive";
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

// A closing fence is a line of nothing but colons, three or more of them.
const CLOSING_FENCE = /^:{3,}\s*$/;

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
// the markers we do not recognise are put back as the exact source text they
// were parsed from, and the read view for an existing article does not move.
function literalSource(node: Directives, source: string): string {
  const start = node.position?.start.offset;
  const end = node.position?.end.offset;
  return start === undefined || end === undefined
    ? `:${node.name}`
    : source.slice(start, end);
}

// Text is not block content, so a marker — a leaf directive or a container's
// fence, both of which sit between paragraphs — needs a paragraph to live in.
function literalParagraph(value: string): Paragraph {
  return { type: "paragraph", children: [{ type: "text", value }] };
}

function literalReplacement(node: Directives, source: string): RootContent {
  const value = literalSource(node, source);
  return node.type === "textDirective"
    ? { type: "text", value }
    : literalParagraph(value);
}

// `:::note[Heads up]` puts the label in a child of its own, but its text is
// already part of the opening line, which we keep verbatim.
function isDirectiveLabel(child: RootContent): boolean {
  return child.type === "paragraph" && child.data?.directiveLabel === true;
}

/**
 * An unrecognised container directive with only its fences made literal.
 *
 * The fences are what nothing claimed; whatever the author nested inside the
 * block is ordinary markdown and stays in the tree. Making the whole block one
 * text node instead would stop that content rendering — emphasis and links
 * would show as their own source, and an image would leave the page entirely.
 */
function literalContainer(
  node: ContainerDirective,
  source: string,
): RootContent[] {
  // Trimmed because an unclosed block ends past the last newline, which would
  // otherwise leave an empty final line where the closing fence would be.
  const lines = literalSource(node, source).trimEnd().split("\n");
  const last = lines[lines.length - 1];
  // An unclosed block runs to the end of whatever encloses it, so there is a
  // closing fence only when the author wrote one.
  const closing =
    lines.length > 1 && CLOSING_FENCE.test(last) ? last : undefined;

  return [
    literalParagraph(lines[0]),
    ...node.children.filter((child) => !isDirectiveLabel(child)),
    ...(closing === undefined ? [] : [literalParagraph(closing)]),
  ];
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

      if (node.type === "containerDirective" && !isGalleryDirective(node)) {
        const kept = literalContainer(node, source);
        (parent.children as RootContent[]).splice(index, 1, ...kept);
        // Carry on at the first node we kept rather than stepping over them:
        // what was nested inside the block is ordinary markdown, and may hold
        // directives of its own.
        return index + 1;
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
