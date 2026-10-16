import {
  $createDirectiveNode,
  $isDirectiveNode,
  $isImageNode,
  Cell,
  DirectiveNode,
  ImageNode,
  createRootEditorSubscription$,
  realmPlugin,
} from "@mdxeditor/editor";
import {
  $getNearestNodeFromDOMNode,
  $getNodeByKey,
  $isElementNode,
  COMMAND_PRIORITY_CRITICAL,
  DRAGOVER_COMMAND,
  DROP_COMMAND,
  type LexicalEditor,
  type LexicalNode,
} from "lexical";
import {
  carriesImage,
  draggedArticleImageFrom,
  imageFilesFrom,
  type DraggedArticleImage,
} from "./gallery-drop";
import {
  galleryImagesFromMdast,
  galleryMdastFromImages,
  isGalleryDirective,
  type GalleryImage,
} from "./gallery-mdast";

export const GALLERY_DROP_TARGET_CLASS = "gallery-drop-target";

export interface GalleryDropParams {
  upload: (file: File) => Promise<string>;
}

// `init` runs once, so the handler cannot be captured there — a later render
// with a different one would be ignored. The cell is republished from
// `update` and read at drop time.
const galleryUpload$ = Cell<((file: File) => Promise<string>) | null>(null);

// What a drop landed on. An image becomes a two-image gallery; a gallery
// grows.
type DropTarget =
  | { kind: "image"; node: ImageNode }
  | { kind: "gallery"; node: DirectiveNode };

function $targetUnder(event: DragEvent): DropTarget | null {
  const from = event.target;
  // The drop lands on whatever DOM is under the pointer; Lexical walks up
  // from there to the node that owns it.
  return from instanceof Node ? $asTarget($getNearestNodeFromDOMNode(from)) : null;
}

function $asTarget(node: LexicalNode | null): DropTarget | null {
  if ($isImageNode(node)) return { kind: "image", node };
  if ($isDirectiveNode(node) && isGalleryDirective(node.getMdastNode())) {
    return { kind: "gallery", node };
  }
  return null;
}

function $targetElement(
  target: DropTarget,
  editor: LexicalEditor,
): HTMLElement | null {
  return editor.getElementByKey(target.node.getKey());
}

function imagesOf(target: DropTarget): GalleryImage[] {
  if (target.kind === "gallery") {
    const mdast = target.node.getMdastNode();
    return isGalleryDirective(mdast) ? galleryImagesFromMdast(mdast) : [];
  }
  const { node } = target;
  const title = node.getTitle();
  return [
    {
      src: node.getSrc(),
      alt: node.getAltText(),
      ...(title ? { title } : {}),
    },
  ];
}

/**
 * Replaces the drop target with a gallery holding `images`, or updates it in
 * place if it already is one.
 */
function $absorb(target: DropTarget, images: GalleryImage[]) {
  if (target.kind === "gallery") {
    target.node.setMdastNode(galleryMdastFromImages(images));
    return;
  }

  const gallery = $createDirectiveNode(galleryMdastFromImages(images));
  const block = target.node.getTopLevelElement();
  if (!$isElementNode(block)) return;

  // A gallery is block-level, so it replaces the image's paragraph — but only
  // when the image was the whole paragraph. An image sitting in a line of
  // prose gets lifted out instead, leaving the prose where the author put it.
  if (block.getChildrenSize() === 1) {
    block.replace(gallery);
  } else {
    target.node.remove();
    block.insertAfter(gallery);
  }
}

function $handleDrop(
  event: DragEvent,
  editor: LexicalEditor,
  upload: (file: File) => Promise<string>,
): boolean {
  const target = $targetUnder(event);
  if (!target || !carriesImage(event.dataTransfer)) return false;

  clearHighlight(editor);
  event.preventDefault();

  const dragged = draggedArticleImageFrom(event.dataTransfer);
  if (dragged) {
    $absorbDragged(target, dragged);
    return true;
  }

  const files = imageFilesFrom(event.dataTransfer);
  if (files.length === 0) return true;

  const targetKey = target.node.getKey();
  void Promise.all(files.map(upload)).then((urls) => {
    editor.update(() => {
      const current = $reReadTarget(targetKey);
      if (current) {
        $absorb(current, [
          ...imagesOf(current),
          ...urls.map((src) => ({ src, alt: "" })),
        ]);
      }
    });
  });
  return true;
}

function $absorbDragged(target: DropTarget, dragged: DraggedArticleImage) {
  const source = $getNodeByKey(dragged.nodeKey);
  // Dropping an image onto itself is a no-op, not a one-image gallery.
  if (source === target.node) return;

  $absorb(target, [
    ...imagesOf(target),
    {
      src: dragged.src,
      alt: dragged.alt,
      ...(dragged.title ? { title: dragged.title } : {}),
    },
  ]);

  if ($isImageNode(source)) {
    const block = source.getTopLevelElement();
    source.remove();
    // The paragraph that held it is now empty and would render as a blank
    // line where the image used to be.
    if ($isElementNode(block) && block.getChildrenSize() === 0) block.remove();
  }
}

// The upload resolves after the drop, by which point the editor may have
// moved on. Node keys survive edits to other parts of the document, so
// re-reading by key is the check for "is the thing we dropped onto still
// here".
function $reReadTarget(key: string): DropTarget | null {
  return $asTarget($getNodeByKey(key));
}

// ------------------------------------------------------------- drop affordance

const highlighted = new WeakMap<LexicalEditor, HTMLElement>();

function clearHighlight(editor: LexicalEditor) {
  highlighted.get(editor)?.classList.remove(GALLERY_DROP_TARGET_CLASS);
  highlighted.delete(editor);
}

function highlight(editor: LexicalEditor, element: HTMLElement) {
  if (highlighted.get(editor) === element) return;
  clearHighlight(editor);
  element.classList.add(GALLERY_DROP_TARGET_CLASS);
  highlighted.set(editor, element);
}

function $handleDragover(event: DragEvent, editor: LexicalEditor): boolean {
  const target = $targetUnder(event);
  if (!target || !carriesImage(event.dataTransfer)) {
    clearHighlight(editor);
    return false;
  }

  const element = $targetElement(target, editor);
  if (element) highlight(editor, element);

  // Without this the browser refuses the drop and no DROP_COMMAND follows.
  event.preventDefault();
  return true;
}

/**
 * Turns a drop onto an image into a gallery, and a drop onto a gallery into
 * one more slide.
 *
 * Registered at critical priority so it runs before the image plugin's own
 * drop handling, which would otherwise insert the image at the caret. When
 * the drop is not over an image or a gallery this returns false and that
 * handling takes over unchanged.
 */
export const galleryDropPlugin = realmPlugin<GalleryDropParams>({
  init(realm, params) {
    if (params) realm.pub(galleryUpload$, params.upload);

    realm.pub(createRootEditorSubscription$, (editor: LexicalEditor) => {
      const teardowns = [
        editor.registerCommand(
          DRAGOVER_COMMAND,
          (event) => $handleDragover(event, editor),
          COMMAND_PRIORITY_CRITICAL,
        ),
        editor.registerCommand(
          DROP_COMMAND,
          (event) => {
            const upload = realm.getValue(galleryUpload$);
            return upload ? $handleDrop(event, editor, upload) : false;
          },
          COMMAND_PRIORITY_CRITICAL,
        ),
      ];

      // DRAGOVER stops firing when the pointer leaves the editor or the drag
      // is abandoned, and neither raises DROP, so the highlight needs its own
      // way out.
      const root = editor.getRootElement();
      const drop = () => {
        clearHighlight(editor);
      };
      root?.addEventListener("dragleave", drop);
      document.addEventListener("dragend", drop);

      return () => {
        teardowns.forEach((teardown) => {
          teardown();
        });
        root?.removeEventListener("dragleave", drop);
        document.removeEventListener("dragend", drop);
      };
    });
  },
  update(realm, params) {
    if (params) realm.pub(galleryUpload$, params.upload);
  },
});
