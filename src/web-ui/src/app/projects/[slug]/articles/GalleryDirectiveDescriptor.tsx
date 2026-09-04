"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  $createImageNode,
  GenericDirectiveEditor,
  type DirectiveDescriptor,
  type DirectiveEditorProps,
} from "@mdxeditor/editor";
import { $createParagraphNode } from "lexical";
import type { ContainerDirective } from "mdast-util-directive";
import { ArticleGallery } from "./ArticleGallery";
import {
  GALLERY_DIRECTIVE_NAME,
  galleryImagesFromMdast,
  galleryMdastFromImages,
  galleryWriteFor,
  isGalleryDirective,
  moveGalleryImage,
  removeGalleryImage,
  type GalleryImage,
} from "./gallery-mdast";

function GalleryEditor({
  mdastNode,
  lexicalNode,
  parentEditor,
}: DirectiveEditorProps<ContainerDirective>) {
  const images = galleryImagesFromMdast(mdastNode);

  const write = (next: readonly GalleryImage[]) => {
    const change = galleryWriteFor(next);
    parentEditor.update(() => {
      if (change.kind === "update") {
        lexicalNode.setMdastNode(galleryMdastFromImages(change.images));
        return;
      }

      if (change.kind === "remove") {
        lexicalNode.remove();
        return;
      }

      // A carousel of one is just an image. Collapsing back is the inverse of
      // the drop that made the gallery, so deleting down is undoable by hand.
      const paragraph = $createParagraphNode();
      paragraph.append(
        $createImageNode({
          src: change.image.src,
          altText: change.image.alt,
          title: change.image.title,
        }),
      );
      lexicalNode.replace(paragraph);
    });
  };

  return (
    <ArticleGallery
      images={images}
      controls={(index) => (
        <>
          <ControlButton
            label="Move image left"
            disabled={index === 0}
            onClick={() => write(moveGalleryImage(images, index, index - 1))}
          >
            <ArrowLeftIcon className="h-4 w-4" />
          </ControlButton>
          <ControlButton
            label="Move image right"
            disabled={index === images.length - 1}
            onClick={() => write(moveGalleryImage(images, index, index + 1))}
          >
            <ArrowRightIcon className="h-4 w-4" />
          </ControlButton>
          <ControlButton
            label="Remove image from gallery"
            onClick={() => write(removeGalleryImage(images, index))}
          >
            <TrashIcon className="h-4 w-4" />
          </ControlButton>
        </>
      )}
      footer={
        <p className="pb-3 text-center text-xs text-muted-foreground">
          Drop an image here to add it to the gallery
        </p>
      }
    />
  );
}

function ControlButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded-md border border-border bg-white p-1.5 text-foreground shadow-sm hover:bg-muted disabled:opacity-30"
    >
      {children}
    </button>
  );
}

export const galleryDirectiveDescriptor: DirectiveDescriptor<ContainerDirective> =
  {
    name: GALLERY_DIRECTIVE_NAME,
    type: "containerDirective",
    attributes: [],
    hasChildren: true,
    testNode: (node) => isGalleryDirective(node),
    Editor: GalleryEditor,
  };

/**
 * Catch-all for directives nothing else claims.
 *
 * `directivesPlugin` makes MDXEditor parse every `:name`, `::name` and
 * `:::name` in the body, and an unclaimed block directive throws
 * `UnrecognizedMarkdownConstructError` rather than degrading — which would
 * make an existing article unopenable. `GenericDirectiveEditor` keeps the
 * node intact so it round-trips to the same markdown.
 *
 * `escapeUnknownTextDirectives` on the plugin covers the inline case
 * (`:smile:` and the like) separately.
 */
export const passthroughDirectiveDescriptor: DirectiveDescriptor = {
  name: "unknown-directive",
  attributes: [],
  hasChildren: true,
  // Block directives only. A text directive that matched here would never
  // reach `escapeUnknownTextDirectives`, which only fires when no descriptor
  // claims the node.
  testNode: (node) => node.type !== "textDirective",
  Editor: GenericDirectiveEditor,
};
