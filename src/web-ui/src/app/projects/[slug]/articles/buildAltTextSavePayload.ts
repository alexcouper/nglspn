import type { SaveImageParameters } from "@mdxeditor/editor";

type EditingImageValues = Omit<SaveImageParameters, "file">;

// The image plugin's editing branch calls setSrc() and setTitle() with whatever
// the payload carries, unconditionally — see saveImage$ in
// @mdxeditor/editor/dist/plugins/image/index.js. Our dialog only edits alt text,
// so both have to be echoed back or saving would blank them on the node.
export function buildAltTextSavePayload(
  initialValues: EditingImageValues,
  altText: string,
): SaveImageParameters {
  return {
    ...initialValues,
    title: initialValues.title ?? "",
    altText,
  };
}
