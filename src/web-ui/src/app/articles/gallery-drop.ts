import type { GalleryImage } from "./gallery-mdast";

// The payload MDXEditor's image plugin writes when one of its images is
// dragged (plugins/image/index.js, `onDragStart`). Reading it is how a drop
// tells "an image from elsewhere in this article" from "a file off the
// desktop".
const LEXICAL_DRAG_TYPE = "application/x-lexical-drag";

export interface DraggedArticleImage extends GalleryImage {
  /** Lexical node key of the image being moved, so it can be removed. */
  nodeKey: string;
}

function imageFileItems(dataTransfer: DataTransfer): DataTransferItem[] {
  return [...dataTransfer.items].filter(
    (item) => item.kind === "file" && item.type.startsWith("image/"),
  );
}

export function imageFilesFrom(dataTransfer: DataTransfer | null): File[] {
  if (!dataTransfer) return [];
  return imageFileItems(dataTransfer)
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null);
}

export function draggedArticleImageFrom(
  dataTransfer: DataTransfer | null,
): DraggedArticleImage | null {
  const raw = dataTransfer?.getData(LEXICAL_DRAG_TYPE);
  if (!raw) return null;

  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    (payload as { type?: unknown }).type !== "image"
  ) {
    return null;
  }

  const data = (payload as { data?: unknown }).data;
  if (typeof data !== "object" || data === null) return null;

  const { src, altText, title, key } = data as Record<string, unknown>;
  if (typeof src !== "string" || typeof key !== "string") return null;

  return {
    src,
    alt: typeof altText === "string" ? altText : "",
    ...(typeof title === "string" && title ? { title } : {}),
    nodeKey: key,
  };
}

/**
 * True if this drag carries something a gallery can absorb.
 *
 * Only inspects what a browser exposes mid-drag: during `dragover` the items
 * are in protected mode, so `getData` returns "" and `getAsFile` returns null.
 * Kinds, types and `types` are readable throughout, and they are enough to
 * decide whether to offer the drop.
 */
export function carriesImage(dataTransfer: DataTransfer | null): boolean {
  if (!dataTransfer) return false;
  return (
    imageFileItems(dataTransfer).length > 0 ||
    [...dataTransfer.types].includes(LEXICAL_DRAG_TYPE)
  );
}
