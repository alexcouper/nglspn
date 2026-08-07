"use client";

import {
  closeImageDialog$,
  imageDialogState$,
  saveImage$,
  useCellValue,
  usePublisher,
} from "@mdxeditor/editor";
import { buildAltTextSavePayload } from "./buildAltTextSavePayload";
import { ImageAltDialog } from "./ImageAltDialog";

// Replaces MDXEditor's stock image dialog. Inserting no longer goes through a
// dialog at all (see InsertImageButton), so the "new" state can never be
// reached — this only ever serves the settings button on an existing image.
export function ArticleImageDialog() {
  const state = useCellValue(imageDialogState$);
  const saveImage = usePublisher(saveImage$);
  const closeImageDialog = usePublisher(closeImageDialog$);

  if (state.type !== "editing") return null;

  return (
    <ImageAltDialog
      initialAltText={state.initialValues.altText ?? ""}
      onSave={(altText) => {
        saveImage(buildAltTextSavePayload(state.initialValues, altText));
      }}
      onCancel={() => {
        closeImageDialog();
      }}
    />
  );
}
